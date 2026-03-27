"""
routes/floorplan.py — Floor plan editor API endpoints.

Handles:
  - Saving edited floor plans
  - Triggering 3D model regeneration from updated layouts
  - Real-time compliance validation
  - DXF export (server-side with ezdxf)
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import List, Dict, Any
import json
import uuid
from datetime import datetime

from database import get_db, Project, DesignVariant
from auth import get_current_user
from schemas.design import Room, FloorPlanUpdate
import ezdxf
from shapely.geometry import Polygon, box
from shapely.ops import unary_union
import io

router = APIRouter()

# ─────────────────────────────────────────────────────────────────────────────
# Floor plan validation and compliance
# ─────────────────────────────────────────────────────────────────────────────

def validate_floor_plan(rooms: List[Room], plot_width: float, plot_depth: float, 
                        plot_area: float, fsi_allowed: float, floors: int) -> Dict[str, Any]:
    """
    Validate floor plan layout and return compliance results.
    
    Returns:
        Dict with validation results including FSI check, overlaps, boundary violations
    """
    issues = []
    warnings = []
    
    # Calculate FSI
    total_built_up = sum(r.w * r.h for r in rooms) * floors
    fsi_used = total_built_up / plot_area
    fsi_ok = fsi_used <= fsi_allowed
    
    if not fsi_ok:
        excess = (fsi_used - fsi_allowed) * plot_area
        issues.append(f"FSI {fsi_used:.2f} exceeds limit {fsi_allowed} — reduce by {excess:.1f} m²")
    
    # Check for overlapping rooms using Shapely
    room_polygons = []
    for room in rooms:
        poly = box(room.x, room.y, room.x + room.w, room.y + room.h)
        room_polygons.append((room, poly))
    
    # Check overlaps
    for i, (room_a, poly_a) in enumerate(room_polygons):
        for j, (room_b, poly_b) in enumerate(room_polygons[i+1:], i+1):
            if poly_a.intersects(poly_b) and not poly_a.touches(poly_b):
                overlap_area = poly_a.intersection(poly_b).area
                if overlap_area > 0.01:  # Ignore tiny overlaps
                    issues.append(f'"{room_a.name}" overlaps with "{room_b.name}" ({overlap_area:.1f} m²)')
    
    # Check boundary violations
    plot_boundary = box(0, 0, plot_width, plot_depth)
    for room in rooms:
        room_poly = box(room.x, room.y, room.x + room.w, room.y + room.h)
        if not plot_boundary.contains(room_poly):
            issues.append(f'"{room.name}" extends outside plot boundary')
    
    # Check required rooms
    room_types = {r.type for r in rooms}
    if floors > 1 and "staircase" not in room_types:
        warnings.append("No staircase defined — required for multi-floor building")
    
    if not any(t in room_types for t in ["bathroom", "master_bedroom"]):
        warnings.append("No bathroom found on this floor")
    
    return {
        "passed": len(issues) == 0,
        "fsi_ok": fsi_ok,
        "fsi_used": fsi_used,
        "fsi_allowed": fsi_allowed,
        "total_built_up": total_built_up,
        "issues": issues,
        "warnings": warnings
    }

# ─────────────────────────────────────────────────────────────────────────────
# API endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/projects/{project_id}/floorplan/save")
async def save_floor_plan(
    project_id: str,
    floor_plan: FloorPlanUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Save updated floor plan layout to database."""
    
    # Get project and verify ownership
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project.user_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Validate the floor plan
    validation = validate_floor_plan(
        floor_plan.rooms,
        project.plot_width_m or 20,  # Default fallback
        project.plot_depth_m or 15,
        project.plot_area_sqm,
        project.fsi_allowed or 2.0,
        project.floors
    )
    
    # Update the project's design DNA with new room layout
    updated_dna = project.design_dna.copy() if project.design_dna else {}
    updated_dna["rooms"] = [room.dict() for room in floor_plan.rooms]
    updated_dna["last_edited"] = datetime.utcnow().isoformat()
    updated_dna["validation"] = validation
    
    # Save to database
    await db.execute(
        update(Project)
        .where(Project.id == project_id)
        .values(
            design_dna=updated_dna,
            updated_at=datetime.utcnow()
        )
    )
    await db.commit()
    
    return {
        "status": "saved",
        "project_id": project_id,
        "validation": validation,
        "rooms_count": len(floor_plan.rooms),
        "total_area": validation["total_built_up"]
    }

@router.post("/projects/{project_id}/floorplan/regenerate-3d")
async def regenerate_3d_model(
    project_id: str,
    floor_plan: FloorPlanUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Trigger 3D model regeneration from updated floor plan."""
    
    # Get project and verify ownership
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project.user_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Validate first
    validation = validate_floor_plan(
        floor_plan.rooms,
        project.plot_width_m or 20,
        project.plot_depth_m or 15,
        project.plot_area_sqm,
        project.fsi_allowed or 2.0,
        project.floors
    )
    
    if not validation["passed"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Floor plan has {len(validation['issues'])} validation issues. Fix them before regenerating 3D model."
        )
    
    # Save the updated layout first
    updated_dna = project.design_dna.copy() if project.design_dna else {}
    updated_dna["rooms"] = [room.dict() for room in floor_plan.rooms]
    updated_dna["last_edited"] = datetime.utcnow().isoformat()
    
    await db.execute(
        update(Project)
        .where(Project.id == project_id)
        .values(
            design_dna=updated_dna,
            status="regenerating",
            updated_at=datetime.utcnow()
        )
    )
    await db.commit()
    
    # Trigger the 3D generation pipeline
    # This would normally call the orchestrator to run layout -> 3D -> VR agents
    # For now, we'll simulate this by updating the project status
    
    try:
        # Import here to avoid circular imports
        from agents.orchestrator import run_pipeline
        from core.memory_store import _get_redis
        
        # Prepare inputs for the pipeline
        inputs = {
            "project_id": project_id,
            "user_id": current_user["id"],
            "rooms": [room.dict() for room in floor_plan.rooms],
            "regenerate_3d_only": True,  # Skip layout generation, go straight to 3D
            "plot_width": project.plot_width_m or 20,
            "plot_depth": project.plot_depth_m or 15,
            "floors": project.floors,
            "style_preferences": project.style_preferences or {}
        }
        
        # Run the pipeline asynchronously (this will trigger WebSocket updates)
        # The orchestrator will handle 3D model generation and VR scene creation
        pipeline_result = await run_pipeline(inputs, db)
        
        return {
            "status": "regenerating",
            "project_id": project_id,
            "message": "3D model regeneration started. Check WebSocket for progress updates.",
            "validation": validation
        }
        
    except Exception as e:
        # Revert project status on error
        await db.execute(
            update(Project)
            .where(Project.id == project_id)
            .values(status="ready")
        )
        await db.commit()
        
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start 3D regeneration: {str(e)}"
        )

@router.get("/projects/{project_id}/floorplan/validate")
async def validate_floor_plan_endpoint(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get current floor plan validation status."""
    
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project.user_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Extract rooms from design DNA
    rooms_data = project.design_dna.get("rooms", []) if project.design_dna else []
    rooms = [Room(**room_data) for room_data in rooms_data]
    
    validation = validate_floor_plan(
        rooms,
        project.plot_width_m or 20,
        project.plot_depth_m or 15,
        project.plot_area_sqm,
        project.fsi_allowed or 2.0,
        project.floors
    )
    
    return validation

@router.get("/projects/{project_id}/floorplan/export/dxf")
async def export_dxf(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Export floor plan as DXF file using ezdxf."""
    
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project.user_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Extract rooms from design DNA
    rooms_data = project.design_dna.get("rooms", []) if project.design_dna else []
    
    if not rooms_data:
        raise HTTPException(status_code=400, detail="No floor plan data found")
    
    # Create DXF document
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    
    # Add layers for different room types
    room_types = set(room["type"] for room in rooms_data)
    for room_type in room_types:
        doc.layers.new(name=room_type.upper(), dxfattribs={"color": 7})
    
    # Add rooms as rectangles with labels
    for room_data in rooms_data:
        room = Room(**room_data)
        
        # Convert to mm (DXF standard)
        x1, y1 = room.x * 1000, room.y * 1000
        x2, y2 = (room.x + room.w) * 1000, (room.y + room.h) * 1000
        
        # Add rectangle
        points = [(x1, y1), (x2, y1), (x2, y2), (x1, y2), (x1, y1)]
        msp.add_lwpolyline(
            points,
            dxfattribs={"layer": room.type.upper()}
        )
        
        # Add text label
        center_x, center_y = (x1 + x2) / 2, (y1 + y2) / 2
        area = room.w * room.h
        label = f"{room.name}\n{area:.1f} m²"
        
        msp.add_text(
            label,
            dxfattribs={
                "layer": room.type.upper(),
                "height": 200,  # 200mm text height
                "style": "Standard"
            }
        ).set_pos((center_x, center_y), align="MIDDLE_CENTER")
    
    # Add plot boundary
    plot_w = (project.plot_width_m or 20) * 1000
    plot_h = (project.plot_depth_m or 15) * 1000
    
    boundary_points = [(0, 0), (plot_w, 0), (plot_w, plot_h), (0, plot_h), (0, 0)]
    msp.add_lwpolyline(
        boundary_points,
        dxfattribs={"layer": "BOUNDARY", "color": 1}  # Red boundary
    )
    
    # Save to bytes
    buffer = io.BytesIO()
    doc.write(buffer)
    buffer.seek(0)
    
    from fastapi.responses import StreamingResponse
    
    return StreamingResponse(
        io.BytesIO(buffer.getvalue()),
        media_type="application/dxf",
        headers={"Content-Disposition": f"attachment; filename=archai-{project_id[:8]}.dxf"}
    )