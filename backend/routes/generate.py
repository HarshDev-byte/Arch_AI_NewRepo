"""
routes/generate.py — Trigger the 8-agent pipeline for a project.

Endpoints
---------
POST /api/generate/start/{project_id}
    - Validates the project exists & is in a triggerable state
    - Writes inputs to the Project row
    - Launches run_and_persist() as a FastAPI BackgroundTask
    - Returns immediately with {"status": "started"}

GET  /api/generate/status/{project_id}
    - Lightweight poll endpoint (no DB query — just checks agent_runs)
    - Returns per-agent status so the frontend can render without WebSocket

The WebSocket at /ws/{project_id} (registered in main.py) is the primary
real-time channel.  The callback here writes to it via app.state.manager.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from auth import OptionalUser, get_current_user
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
from core.memory_store import (
    cache_project_result,
    check_rate_limit,
    increment_generation_count,
    invalidate_project_cache,
)

router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# Request schema
# ─────────────────────────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    """Optional request body for /start — if omitted, uses values stored on Project."""
    latitude:          float | None = None
    longitude:         float | None = None
    plot_area_sqm:     float | None = None
    budget_inr:        int   | None = None
    floors:            int          = Field(default=2, ge=1, le=20)
    style_preferences: list[str]    = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# Agent-run persistence helpers
# ─────────────────────────────────────────────────────────────────────────────

async def _upsert_agent_run(
    project_id: uuid.UUID,
    agent_name: str,
    status: str,
    output_data: dict[str, Any] | None = None,
    error_message: str | None = None,
) -> None:
    """
    Insert or update the AgentRun row for this agent.
    Uses a fresh session so it doesn't conflict with the background-task flow.
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(AgentRun).where(
                AgentRun.project_id == project_id,
                AgentRun.agent_name == agent_name,
            )
        )
        run = result.scalar_one_or_none()

        now = datetime.now(timezone.utc)

        if run is None:
            run = AgentRun(
                project_id=project_id,
                agent_name=agent_name,
                status=status,
                started_at=now if status == "running" else None,
                output_data=output_data,
                error_message=error_message,
            )
            db.add(run)
        else:
            run.status = status
            if status == "running" and run.started_at is None:
                run.started_at = now
            if status in ("complete", "error"):
                run.completed_at = now
            if output_data:
                run.output_data = output_data
            if error_message:
                run.error_message = error_message

        await db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Background execution task
# ─────────────────────────────────────────────────────────────────────────────

async def _run_pipeline_bg(
    project_id: str,
    inputs: dict[str, Any],
    manager: Any,
    user_id: str | None = None,
) -> None:
    """
    Full pipeline execution + persistence.  Runs as a BackgroundTask so the
    POST /start endpoint returns immediately.
    """
    pid = uuid.UUID(project_id)

    # ── Mark project as processing ────────────────────────────────────────────
    async with AsyncSessionLocal() as db:
        r = await db.execute(select(Project).where(Project.id == pid))
        proj = r.scalar_one_or_none()
        if proj is None:
            return
        proj.status        = "processing"
        proj.latitude      = inputs.get("latitude")
        proj.longitude     = inputs.get("longitude")
        proj.plot_area_sqm = inputs.get("plot_area_sqm")
        proj.budget_inr    = inputs.get("budget_inr")
        proj.floors        = inputs.get("floors", 2)
        proj.style_preferences = inputs.get("style_preferences", [])
        await db.commit()

    # ── Build progress callback ────────────────────────────────────────────────
    async def progress_callback(payload: dict[str, Any]) -> None:
        # 1. WebSocket broadcast
        try:
            await manager.send_update(project_id, payload)
        except Exception:
            pass

        # 2. Persist agent-run row
        agent = payload.get("agent", "")
        pstatus = payload.get("status", "")
        if agent and agent not in ("orchestrator", "system"):
            await _upsert_agent_run(
                project_id=pid,
                agent_name=agent,
                status=pstatus,
                output_data=payload.get("data") or None,
                error_message=payload.get("message") if pstatus == "error" else None,
            )

    # ── Run orchestrator ───────────────────────────────────────────────────────
    try:
        from agents.orchestrator import run_pipeline
        final = await run_pipeline(
            project_id=project_id,
            latitude=float(inputs["latitude"]),
            longitude=float(inputs["longitude"]),
            plot_area_sqm=float(inputs["plot_area_sqm"]),
            budget_inr=int(inputs["budget_inr"]),
            floors=int(inputs.get("floors", 2)),
            style_preferences=list(inputs.get("style_preferences", [])),
            progress_callback=progress_callback,
            user_id=user_id,
        )
    except Exception as exc:
        # Mark project error + notify frontend
        async with AsyncSessionLocal() as db:
            r = await db.execute(select(Project).where(Project.id == pid))
            proj = r.scalar_one_or_none()
            if proj:
                proj.status = "error"
                await db.commit()
        try:
            await manager.send_update(project_id, {
                "agent":   "system",
                "status":  "error",
                "message": f"Pipeline error: {exc}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        except Exception:
            pass
        return

    # ── Persist all outputs ────────────────────────────────────────────────────
    async with AsyncSessionLocal() as db:
        r = await db.execute(select(Project).where(Project.id == pid))
        proj = r.scalar_one_or_none()
        if proj is None:
            return

        errors = final.get("errors") or []
        proj.status      = "complete" if not errors else "error"
        proj.design_seed = final.get("design_seed")
        proj.design_dna  = final.get("best_dna")

        # GeoAnalysis ──────────────────────────────────────────────────────────
        geo = final.get("geo_data") or {}
        if geo and proj.geo_analysis is None:
            db.add(GeoAnalysis(
                project_id=pid,
                plot_data=geo,
                zoning_type=geo.get("zoning_type"),
                fsi_allowed=geo.get("fsi_allowed"),
                road_access=geo.get("road_access"),
                nearby_amenities=geo.get("nearby_amenities"),
                solar_irradiance=geo.get("solar_irradiance_kwh_m2_day"),
            ))

        # DesignVariants ───────────────────────────────────────────────────────
        for v in (final.get("design_variants") or []):
            db.add(DesignVariant(
                project_id=pid,
                variant_number=v.get("variant_number"),
                dna=v.get("dna"),
                score=v.get("score"),
                is_selected=v.get("is_selected", False),
                floor_plan_svg=(final.get("layout_data") or {}).get("floor_plan_svg"),
            ))

        # CostEstimate ─────────────────────────────────────────────────────────
        cost = final.get("cost_data") or {}
        if cost and proj.cost_estimate is None:
            db.add(CostEstimate(
                project_id=pid,
                breakdown=cost.get("breakdown"),
                total_cost_inr=cost.get("total_cost_inr"),
                cost_per_sqft=cost.get("cost_per_sqft_actual"),
                roi_estimate=cost.get("roi"),
            ))

        # ComplianceCheck ──────────────────────────────────────────────────────
        comp = final.get("compliance_data") or {}
        if comp and proj.compliance_check is None:
            db.add(ComplianceCheck(
                project_id=pid,
                fsi_used=comp.get("fsi_used"),
                fsi_allowed=comp.get("fsi_allowed"),
                setback_compliance=comp.get("setback_compliance"),
                height_compliance=(comp.get("height_compliance") or {}).get("ok"),
                parking_required=comp.get("parking_required"),
                green_area_required=(comp.get("green_area") or {}).get("required_sqm"),
                issues=comp.get("issues", []),
                passed=comp.get("passed"),
            ))

        await db.commit()

    # ── Increment generation counter + cache pipeline result in Redis ──────────
    if user_id:
        await increment_generation_count(user_id)
    await cache_project_result(project_id, {
        k: v for k, v in dict(final).items()
        if k != "progress_callback"   # strip non-serialisable callback
    })

    # ── Final WebSocket summary ────────────────────────────────────────────────
    sust      = final.get("sustainability_data") or {}
    variants  = final.get("design_variants") or []
    n_done    = len(final.get("completed_agents") or [])
    n_errors  = len(errors)

    summary = {
        "agent":            "system",
        "status":           "complete",
        "event":            "pipeline_complete",
        "message":          f"All done! {n_done} agents completed, {n_errors} error(s).",
        "project_id":       project_id,
        "variants_count":   len(variants),
        "total_cost":       (final.get("cost_data") or {}).get("total_cost_inr"),
        "compliance_passed":(final.get("compliance_data") or {}).get("passed"),
        "green_rating":     sust.get("green_rating"),
        "green_score":      sust.get("green_score"),
        "best_score":       variants[0].get("score") if variants else None,
        "errors":           errors,
        "timestamp":        datetime.now(timezone.utc).isoformat(),
    }
    try:
        await manager.send_update(project_id, summary)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/generate/start/{project_id}
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/start/{project_id}",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger the 8-agent pipeline for an existing project",
)
async def start_generation(
    project_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    body: GenerateRequest = GenerateRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(OptionalUser()),
):
    # Validate UUID
    try:
        pid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project_id UUID")

    # Fetch project
    result = await db.execute(select(Project).where(Project.id == pid))
    proj   = result.scalar_one_or_none()
    if proj is None:
        raise HTTPException(status_code=404, detail="Project not found")

    # Prevent double-triggering
    if proj.status == "processing":
        raise HTTPException(status_code=409, detail="Pipeline already running for this project")

    # Merge: body fields override project DB fields; DB fields act as fallback
    inputs: dict[str, Any] = {
        "latitude":          body.latitude          if body.latitude          is not None else proj.latitude,
        "longitude":         body.longitude         if body.longitude         is not None else proj.longitude,
        "plot_area_sqm":     body.plot_area_sqm     if body.plot_area_sqm     is not None else proj.plot_area_sqm,
        "budget_inr":        body.budget_inr        if body.budget_inr        is not None else proj.budget_inr,
        "floors":            body.floors            if body.floors != 2        else (proj.floors or 2),
        "style_preferences": body.style_preferences if body.style_preferences else (proj.style_preferences or []),
    }

    # Validate required fields are present from either source
    missing = [k for k in ("latitude", "longitude", "plot_area_sqm", "budget_inr") if inputs.get(k) is None]
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Missing required fields: {missing}. Supply via request body or save on the Project first.",
        )

    # Rate-limit check for authenticated users
    if current_user:
        allowed, info = await check_rate_limit(current_user["user_id"])
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Try again in {info} seconds.",
                headers={"Retry-After": str(info)},
            )

    uid     = current_user["user_id"] if current_user else None
    manager = request.app.state.manager
    background_tasks.add_task(_run_pipeline_bg, project_id, inputs, manager, uid)

    return {
        "status":     "started",
        "project_id": project_id,
        "message":    "Pipeline launched. Connect to /ws/{project_id} for real-time updates.",
        "inputs":     inputs,
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/generate/status/{project_id}
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/status/{project_id}",
    summary="Poll per-agent status (no WebSocket required)",
)
async def get_generation_status(
    project_id: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        pid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project_id UUID")

    proj_result = await db.execute(select(Project).where(Project.id == pid))
    proj        = proj_result.scalar_one_or_none()
    if proj is None:
        raise HTTPException(status_code=404, detail="Project not found")

    runs_result = await db.execute(
        select(AgentRun).where(AgentRun.project_id == pid)
    )
    runs = runs_result.scalars().all()

    return {
        "project_id":        project_id,
        "project_status":    proj.status,
        "agents": [
            {
                "agent_name":   r.agent_name,
                "status":       r.status,
                "started_at":   r.started_at.isoformat() if r.started_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                "error":        r.error_message,
                "data":         r.output_data,
            }
            for r in runs
        ],
    }

@router.post(
    "/{project_id}/complete",
    summary="Manually mark project as complete (for debugging)",
)
async def complete_project(
    project_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Manually mark a project as complete if all agents have finished.
    This is a debugging endpoint to fix stuck projects.
    """
    pid = uuid.UUID(project_id)
    
    # Get project and verify ownership
    result = await db.execute(select(Project).where(Project.id == pid))
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if str(project.user_id) != user["user_id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Check agent runs
    agent_result = await db.execute(
        select(AgentRun).where(AgentRun.project_id == pid)
    )
    agent_runs = agent_result.scalars().all()
    
    completed_agents = sum(1 for run in agent_runs if run.status == "complete")
    error_agents = sum(1 for run in agent_runs if run.status == "error")
    total_agents = len(agent_runs)
    
    if total_agents == 0:
        raise HTTPException(status_code=400, detail="No agent runs found")
    
    if error_agents > 0:
        # Update to error status
        await db.execute(
            update(Project)
            .where(Project.id == pid)
            .values(status="error")
        )
        await db.commit()
        return {
            "status": "error",
            "message": f"Project marked as error due to {error_agents} failed agents",
            "completed_agents": completed_agents,
            "error_agents": error_agents,
            "total_agents": total_agents
        }
    
    elif completed_agents == total_agents:
        # All agents complete, mark project as complete
        await db.execute(
            update(Project)
            .where(Project.id == pid)
            .values(status="complete")
        )
        await db.commit()
        return {
            "status": "complete",
            "message": f"Project marked as complete with {completed_agents} successful agents",
            "completed_agents": completed_agents,
            "error_agents": error_agents,
            "total_agents": total_agents
        }
    
    else:
        return {
            "status": "processing",
            "message": f"Project still processing: {completed_agents}/{total_agents} agents complete",
            "completed_agents": completed_agents,
            "error_agents": error_agents,
            "total_agents": total_agents
        }