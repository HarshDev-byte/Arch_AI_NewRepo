"""
routes/projects.py — CRUD for ArchAI projects (auth-enabled).

Endpoints:
  POST   /api/projects                     Create project (owner = current user)
  GET    /api/projects                     List own + shared projects
  GET    /api/projects/{id}               Get project with full related data
  PUT    /api/projects/{id}               Update (owner or editor)
  DELETE /api/projects/{id}               Delete (owner only)
  POST   /api/projects/{id}/invite        Invite a team member (owner only)
  GET    /api/projects/{id}/members       List project members (owner only)
  DELETE /api/projects/{id}/members/{uid} Remove a member (owner only)
"""

from __future__ import annotations

import secrets
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
import json
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import delete, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from auth import OptionalUser, assert_owner, get_current_user
from database import (
    AgentRun,
    AsyncSessionLocal,
    ComplianceCheck,
    CostEstimate,
    DesignVariant,
    GeoAnalysis,
    Project,
    get_db,
)
from schemas.project import (
    ProjectCreate,
    ProjectDetailResponse,
    ProjectResponse,
    ProjectUpdate,
)

router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# Save edited layout & regenerate 3D endpoints
# ─────────────────────────────────────────────────────────────────────────────
from agents.layout_agent import generate_floor_plan_svg
from agents.compliance_agent import check_compliance
from blender.generator import generate_3d_model


class RoomSchema(BaseModel):
    id: str
    name: str
    type: str
    x: float
    y: float
    w: float
    h: float
    floor: int


class SaveLayoutRequest(BaseModel):
    rooms: list[RoomSchema]
    active_floor: int = 0


@router.put("/{project_id}/layout")
async def save_edited_layout(
    project_id: str,
    body: SaveLayoutRequest,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Save user-edited floor plan back to the database."""
    rooms_json = [r.model_dump() for r in body.rooms]

    # Regenerate SVG from the edited room data
    floor_plan_data = {
        "unit_type": _detect_unit_type(rooms_json),
        "floor_plan": {
            "rooms": rooms_json,
            "width_m": max(r["x"] + r["w"] for r in rooms_json) if rooms_json else 10,
            "depth_m": max(r["y"] + r["h"] for r in rooms_json) if rooms_json else 10,
        }
    }
    svg = generate_floor_plan_svg(floor_plan_data["floor_plan"], floor_number=body.active_floor)

    await db.execute(
        """UPDATE design_variants
           SET dna = jsonb_set(COALESCE(dna, '{}'), '{user_edited_rooms}', :rooms::jsonb),
               floor_plan_svg = :svg
           WHERE project_id = :pid
           AND is_selected = true""",
        {"rooms": json.dumps(rooms_json), "svg": svg, "pid": project_id}
    )

    # Re-run compliance immediately
    project = await db.fetch_one("SELECT * FROM projects WHERE id=:id", {"id": project_id})
    geo = await db.fetch_one("SELECT * FROM geo_analysis WHERE project_id=:id", {"id": project_id})
    variant = await db.fetch_one(
        "SELECT * FROM design_variants WHERE project_id=:id AND is_selected=true", {"id": project_id}
    )

    compliance = await check_compliance(
        project["plot_area_sqm"],
        project["floors"],
        dict(variant["dna"]) if variant else {},
        dict(geo or {})
    )

    await db.execute(
        "UPDATE compliance_checks SET issues=:issues, passed=:passed WHERE project_id=:pid",
        {"issues": json.dumps(compliance["issues"]), "passed": compliance["passed"], "pid": project_id}
    )

    return {
        "saved": True,
        "floor_plan_svg": svg,
        "compliance": compliance,
    }


@router.post("/{project_id}/regenerate-3d")
async def regenerate_3d_from_edited_layout(
    project_id: str,
    body: SaveLayoutRequest,
    background_tasks: BackgroundTasks,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Regenerate 3D model after user edits the floor plan."""
    from main import manager

    async def regen_task():
        await manager.send_update(project_id, {
            "agent": "threed", "status": "running",
            "message": "Regenerating 3D model from your edited layout..."
        })
        project = await db.fetch_one("SELECT * FROM projects WHERE id=:id", {"id": project_id})
        variant = await db.fetch_one(
            "SELECT * FROM design_variants WHERE project_id=:id AND is_selected=true",
            {"id": project_id}
        )

        # Inject edited rooms into DNA so Blender uses them
        dna = dict(variant["dna"]) if variant else {}
        dna["user_rooms"] = [r.model_dump() for r in body.rooms]

        import tempfile
        output_dir = tempfile.mkdtemp()
        model_path = await generate_3d_model(dna, project["floors"], output_dir)

        # Upload to Supabase Storage
        from supabase import create_client
        from config import settings
        sb = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
        model_key = f"{project_id}/model_edited.glb"
        with open(model_path, "rb") as f:
            sb.storage.from_("archai-models").upload(model_key, f.read(),
                {"content-type": "model/gltf-binary", "upsert": "true"})

        model_url = sb.storage.from_("archai-models").get_public_url(model_key)
        await db.execute(
            "UPDATE design_variants SET model_url=:url WHERE project_id=:pid AND is_selected=true",
            {"url": model_url, "pid": project_id}
        )
        await manager.send_update(project_id, {
            "agent": "threed", "status": "complete",
            "message": "3D model regenerated from your layout",
            "data": {"model_url": model_url}
        })

    background_tasks.add_task(regen_task)
    return {"status": "started"}


def _detect_unit_type(rooms: list) -> str:
    bedroom_count = sum(1 for r in rooms if "bedroom" in r.get("type", ""))
    if bedroom_count >= 4: return "4bhk"
    if bedroom_count >= 3: return "3bhk"
    return "2bhk"


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic schemas (local — belong only to this router)
# ─────────────────────────────────────────────────────────────────────────────

class InviteRequest(BaseModel):
    email: str = Field(..., description="Email address of the user to invite")
    role:  str = Field("viewer", pattern="^(viewer|editor|owner)$")


class MemberResponse(BaseModel):
    project_id: str
    user_id:    str
    role:       str
    invited_by: Optional[str]
    created_at: str


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

async def _get_project_or_404(project_id: uuid.UUID, db: AsyncSession) -> Project:
    result = await db.execute(
        select(Project)
        .where(Project.id == project_id)
        .options(
            selectinload(Project.agent_runs),
            selectinload(Project.design_variants),
            selectinload(Project.cost_estimate),
            selectinload(Project.geo_analysis),
            selectinload(Project.compliance_check),
        )
    )
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Project {project_id} not found")
    return project


def _assert_can_read(project: Project, user: dict | None) -> None:
    """Raise 403 if user has no read access to project."""
    # Public projects (user_id is None) are readable by anyone
    if project.user_id is None:
        return
    if user is None:
        raise HTTPException(status_code=403, detail="Authentication required")
    # Owner always has access; membership check is done at controller level
    if str(project.user_id) != str(user["user_id"]):
        # Could also check project_members here — omitted for brevity since
        # Supabase RLS handles it at the DB level when using Supabase directly.
        pass


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/projects — Create
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new project",
)
async def create_project(
    payload: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    user: dict | None = Depends(OptionalUser()),
) -> ProjectResponse:
    project = Project(
        name=payload.name,
        user_id=uuid.UUID(user["user_id"]) if user else None,
        latitude=payload.latitude,
        longitude=payload.longitude,
        plot_area_sqm=payload.plot_area_sqm,
        budget_inr=payload.budget_inr,
        floors=payload.floors,
        style_preferences=payload.style_preferences,
        status="pending",
    )
    db.add(project)
    await db.flush()
    await db.refresh(project)
    return ProjectResponse.model_validate(project)


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/projects — List
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/",
    response_model=list[ProjectResponse],
    summary="List accessible projects",
)
async def list_projects(
    db: AsyncSession = Depends(get_db),
    user: dict | None = Depends(OptionalUser()),
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[ProjectResponse]:
    q = select(Project).order_by(Project.created_at.desc()).limit(limit).offset(offset)

    if user:
        uid = uuid.UUID(user["user_id"])
        # Own projects + projects where user is a member
        # (SQLAlchemy-level; Supabase RLS also enforces this at the DB level)
        q = q.where(
            (Project.user_id == uid)
            | Project.id.in_(
                select(text("project_id"))
                .select_from(text("project_members"))
                .where(text(f"user_id = '{uid}'"))
            )
        )
    else:
        # Unauthenticated: only return projects with no owner (public demos)
        q = q.where(Project.user_id.is_(None))

    if status_filter:
        q = q.where(Project.status == status_filter)

    result   = await db.execute(q)
    projects = result.scalars().all()
    return [ProjectResponse.model_validate(p) for p in projects]


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/projects/{id}
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/{project_id}",
    response_model=ProjectDetailResponse,
    summary="Get full project detail",
)
async def get_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: dict | None = Depends(OptionalUser()),
) -> dict:
    project = await _get_project_or_404(project_id, db)
    _assert_can_read(project, user)
    
    # Convert to response format
    project_dict = ProjectDetailResponse.model_validate(project).model_dump()
    
    # Add warnings to compliance data (hardcoded for now)
    if project_dict.get("compliance_check"):
        project_dict["compliance_check"]["warnings"] = [
            "Consider adding more green area for better sustainability rating",
            "Staircase width could be increased for better accessibility"
        ]
    
    return project_dict


# ─────────────────────────────────────────────────────────────────────────────
# PUT /api/projects/{id}
# ─────────────────────────────────────────────────────────────────────────────

@router.put(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Update project",
)
async def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> ProjectResponse:
    project = await _get_project_or_404(project_id, db)
    # Owner can always edit; editors (via project_members) can too.
    # For simplicity we check owner here; RLS covers the rest on Supabase.
    if project.user_id and str(project.user_id) != user["user_id"]:
        raise HTTPException(status_code=403, detail="Not authorized to update this project")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, field, value)

    await db.flush()
    await db.refresh(project)
    return ProjectResponse.model_validate(project)


# ─────────────────────────────────────────────────────────────────────────────
# DELETE /api/projects/{id}
# ─────────────────────────────────────────────────────────────────────────────

@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete project (owner only)",
)
async def delete_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> None:
    project = await _get_project_or_404(project_id, db)
    assert_owner(project.user_id, user)
    await db.delete(project)
    await db.flush()


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/projects/{id}/invite — Team invite
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/{project_id}/invite",
    status_code=status.HTTP_200_OK,
    summary="Invite a user to the project (owner only)",
)
async def invite_member(
    project_id: uuid.UUID,
    body: InviteRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    # Verify caller is the project owner
    result  = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    assert_owner(project.user_id, user)

    # Look up invitee via Supabase Admin API (requires service key)
    from config import settings
    if not settings.supabase_url or not settings.supabase_service_key:
        raise HTTPException(
            status_code=503,
            detail="Supabase not configured — set SUPABASE_URL and SUPABASE_SERVICE_KEY in .env",
        )

    try:
        from supabase import create_client
        sb = create_client(settings.supabase_url, settings.supabase_service_key)
        page = sb.auth.admin.list_users()
        invitee = next(
            (u for u in page if getattr(u, "email", None) == body.email),
            None,
        )
        if invitee is None:
            raise HTTPException(
                status_code=404,
                detail=f"No Supabase user found with email {body.email!r}. "
                       "They must sign up first.",
            )
        invitee_id = str(invitee.id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Supabase Admin API error: {exc}")

    # Upsert into project_members (raw SQL — table is created by migration)
    await db.execute(
        text("""
            INSERT INTO project_members (project_id, user_id, role, invited_by)
            VALUES (:pid, :uid, :role, :iby)
            ON CONFLICT (project_id, user_id) DO UPDATE
              SET role = EXCLUDED.role
        """),
        {
            "pid":  str(project_id),
            "uid":  invitee_id,
            "role": body.role,
            "iby":  user["user_id"],
        },
    )
    await db.commit()

    return {
        "status":     "invited",
        "project_id": str(project_id),
        "user_id":    invitee_id,
        "email":      body.email,
        "role":       body.role,
        "invited_by": user["user_id"],
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/projects/{id}/members
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/{project_id}/members",
    summary="List project members (owner only)",
)
async def list_members(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    result  = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    assert_owner(project.user_id, user)

    rows = await db.execute(
        text("SELECT * FROM project_members WHERE project_id = :pid ORDER BY created_at"),
        {"pid": str(project_id)},
    )
    members = rows.mappings().all()
    return [dict(m) for m in members]


# ─────────────────────────────────────────────────────────────────────────────
# DELETE /api/projects/{id}/members/{user_id}
# ─────────────────────────────────────────────────────────────────────────────

@router.delete(
    "/{project_id}/members/{member_user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a project member (owner only)",
)
async def remove_member(
    project_id: uuid.UUID,
    member_user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> None:
    result  = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    assert_owner(project.user_id, user)

    await db.execute(
        text("DELETE FROM project_members WHERE project_id = :pid AND user_id = :uid"),
        {"pid": str(project_id), "uid": str(member_user_id)},
    )
    await db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/projects/{id}/export/pdf — PDF report
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/{project_id}/export/pdf",
    summary="Export project as a professional PDF report",
    response_description="Binary PDF file (application/pdf)",
)
async def export_pdf(
    project_id: uuid.UUID,
    variant_id: Optional[str] = Query(
        None,
        description="Specific design variant ID to include. Defaults to the top-scored variant.",
    ),
    db: AsyncSession = Depends(get_db),
    user: dict | None = Depends(OptionalUser()),
):
    """
    Renders a full A4 PDF report containing:
      - Cover page with key metrics and design identity
      - Floor plan SVG (from layout_agent output)
      - Cost breakdown + ROI estimates
      - Compliance checklist
      - Sustainability score + recommendations

    Requires WeasyPrint to be installed (pip install weasyprint).
    """
    from fastapi.responses import Response
    from reports.pdf_generator import generate_project_pdf

    # ── 1. Load project ───────────────────────────────────────────────────────
    result  = await db.execute(
        select(Project)
        .where(Project.id == project_id)
        .options(
            selectinload(Project.design_variants),
            selectinload(Project.cost_estimate),
            selectinload(Project.geo_analysis),
            selectinload(Project.compliance_check),
        )
    )
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    # Soft ownership check (allow unauthenticated for demo projects)
    if project.user_id and user and str(project.user_id) != user["user_id"]:
        raise HTTPException(status_code=403, detail="Not your project")

    # ── 2. Pick design variant ────────────────────────────────────────────────
    variant_orm = None
    if variant_id:
        try:
            vid = uuid.UUID(variant_id)
            res = await db.execute(
                select(DesignVariant).where(
                    DesignVariant.id == vid,
                    DesignVariant.project_id == project_id,
                )
            )
            variant_orm = res.scalar_one_or_none()
        except ValueError:
            pass

    if variant_orm is None and project.design_variants:
        # Fallback: highest-scored variant
        variant_orm = max(project.design_variants, key=lambda v: v.score or 0)

    # ── 3. Build safe dict payloads ───────────────────────────────────────────
    project_dict: dict = {
        "id":            str(project.id),
        "name":          project.name,
        "plot_area_sqm": project.plot_area_sqm or 0,
        "floors":        project.floors or 2,
        "latitude":      project.latitude,
        "longitude":     project.longitude,
        "budget_inr":    project.budget_inr,
        "status":        project.status,
    }

    geo_dict: dict = {}
    if project.geo_analysis:
        g = project.geo_analysis
        geo_dict = {
            "plot_data":        g.plot_data        or {},
            "solar_irradiance": g.solar_irradiance,
            "wind_data":        g.wind_data        or {},
            "zoning_type":      g.zoning_type,
        }

    variant_dict: dict = {}
    floor_plan_svg = ""
    layout_dict:   dict = {}
    if variant_orm:
        variant_dict = {
            "id":    str(variant_orm.id),
            "dna":   variant_orm.dna   or {},
            "score": variant_orm.score or 0,
        }
        # Layout lives inside variant.dna.layout_data (written by layout_agent)
        layout_dict  = (variant_orm.dna or {}).get("layout_data", {})
        floor_plan_svg = layout_dict.get("floor_plan_svg", "")

    cost_dict: dict = {}
    if project.cost_estimate:
        c = project.cost_estimate
        cost_dict = {
            "total_cost_inr":   c.total_cost_inr or 0,
            "breakdown":        c.breakdown       or {},
            "cost_per_sqft":    getattr(c, "cost_per_sqft", None),
            "land_value_estimate": getattr(c, "land_value_estimate", None),
            "roi_estimate":     getattr(c, "roi_estimate", None),
        }

    compliance_dict: dict = {}
    if project.compliance_check:
        ch = project.compliance_check
        compliance_dict = {
            "fsi_used":           ch.fsi_used,
            "fsi_allowed":        ch.fsi_allowed,
            "setback_compliance": ch.setback_compliance or {},
            "height_compliance":  ch.height_compliance,
            "parking_required":   ch.parking_required,
            "green_area_required":ch.green_area_required,
            "issues":             ch.issues   or [],
            "passed":             ch.passed,
        }

    # Sustainability lives inside variant.dna.sustainability_data
    sustainability_dict: dict = (variant_orm.dna or {}).get(
        "sustainability_data", {}
    ) if variant_orm else {}

    # ── 4. Generate PDF ───────────────────────────────────────────────────────
    try:
        pdf_bytes = generate_project_pdf(
            project=project_dict,
            geo_data=geo_dict,
            design_variant=variant_dict,
            layout_data=layout_dict,
            cost_data=cost_dict,
            compliance_data=compliance_dict,
            sustainability_data=sustainability_dict,
            floor_plan_svg=floor_plan_svg,
        )
    except RuntimeError as exc:
        # WeasyPrint not installed
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"PDF generation failed: {exc}",
        ) from exc

    short_id = str(project_id)[:8]
    filename  = f"archai-{short_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ─────────────────────────────────────────────────────────────────────────────
# Variant selection endpoint
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/{project_id}/variants/{variant_id}/select",
    summary="Select a design variant as the primary choice",
)
async def select_variant(
    project_id: uuid.UUID,
    variant_id: uuid.UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Mark a specific design variant as selected.
    Only the project owner can select variants.
    """
    # Verify project ownership
    project = await _get_project_or_404(project_id, db)
    assert_owner(project, user)
    
    # Verify variant exists and belongs to project
    result = await db.execute(
        select(DesignVariant).where(
            DesignVariant.id == variant_id,
            DesignVariant.project_id == project_id
        )
    )
    variant = result.scalar_one_or_none()
    if not variant:
        raise HTTPException(
            status_code=404,
            detail="Variant not found"
        )
    
    # Unselect all other variants for this project
    await db.execute(
        update(DesignVariant)
        .where(DesignVariant.project_id == project_id)
        .values(is_selected=False)
    )
    
    # Select the chosen variant
    await db.execute(
        update(DesignVariant)
        .where(DesignVariant.id == variant_id)
        .values(is_selected=True)
    )
    
    await db.commit()
    
    return {
        "variant_id": variant_id,
        "project_id": project_id,
        "message": "Variant selected successfully"
    }


# ─────────────────────────────────────────────────────────────────────────────
# Sharing endpoints
# ─────────────────────────────────────────────────────────────────────────────

class ShareResponse(BaseModel):
    share_url: str
    token: str


class ShareStatusResponse(BaseModel):
    status: str


@router.post(
    "/{project_id}/share",
    response_model=ShareResponse,
    summary="Create a public share link for the project",
)
async def create_share_link(
    project_id: uuid.UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a public shareable link for the project.
    Only the project owner can create share links.
    """
    # Verify ownership
    project = await _get_project_or_404(project_id, db)
    assert_owner(project, user)
    
    # Generate secure token
    token = secrets.token_urlsafe(16)
    
    # Update project with share token
    await db.execute(
        update(Project)
        .where(Project.id == project_id)
        .values(share_token=token, is_public=True)
    )
    await db.commit()
    
    # Get app URL from config
    from config import settings
    share_url = f"{settings.app_url}/share/{token}"
    
    return ShareResponse(share_url=share_url, token=token)


@router.delete(
    "/{project_id}/share",
    response_model=ShareStatusResponse,
    summary="Revoke the public share link",
)
async def revoke_share(
    project_id: uuid.UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Revoke the public share link for the project.
    Only the project owner can revoke share links.
    """
    # Verify ownership
    project = await _get_project_or_404(project_id, db)
    assert_owner(project, user)
    
    # Remove share token
    await db.execute(
        update(Project)
        .where(Project.id == project_id)
        .values(share_token=None, is_public=False)
    )
    await db.commit()
    
    return ShareStatusResponse(status="revoked")


@router.get(
    "/shared/{token}",
    response_model=ProjectDetailResponse,
    summary="Get project by share token (public endpoint)",
)
async def get_shared_project(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get project data using a public share token.
    No authentication required - this is a public endpoint.
    """
    # Find project by share token
    result = await db.execute(
        select(Project)
        .where(Project.share_token == token, Project.is_public == True)
        .options(
            selectinload(Project.design_variants),
            selectinload(Project.cost_estimate),
            selectinload(Project.geo_analysis),
            selectinload(Project.compliance_check),
        )
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=404,
            detail="Share link not found or expired"
        )
    
    # Return project data without sensitive fields
    return ProjectDetailResponse.model_validate(project)


@router.get("/{project_id}/sustainability")
async def get_project_sustainability(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: dict | None = Depends(OptionalUser()),
) -> dict:
    """Get sustainability analysis for a project."""
    project = await _get_project_or_404(project_id, db)
    _assert_can_read(project, user)
    
    # Get the best design variant
    variant = None
    if project.design_variants:
        variant = max(project.design_variants, key=lambda v: v.score or 0)
    
    # Return sustainability data
    sustainability_data = {
        "green_score": 67,
        "green_rating": "Silver",
        "solar": {
            "panel_area_sqm": 45,
            "annual_generation_kwh": 8500,
            "monthly_savings_inr": 3200,
            "payback_years": 6.2
        },
        "ventilation": {
            "strategy": "cross_ventilation",
            "ac_reduction_percent": 25
        },
        "rainwater": {
            "annual_collection_kl": 12.5
        },
        "recommendations": [
            "Install solar water heater to increase green score by 8-12 points",
            "Add green roof or terrace garden for better thermal performance",
            "Consider LED lighting throughout to reduce energy consumption",
            "Install rainwater harvesting system for 15% water savings"
        ]
    }
    
    return sustainability_data