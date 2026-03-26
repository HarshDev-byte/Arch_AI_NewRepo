"""
routes/agents.py — Agent status and management endpoints.

Endpoints:
  GET  /api/agents/{project_id}/status   List all agent runs for a project
  GET  /api/agents/{project_id}/{agent}  Get a single agent run detail
  POST /api/agents/{project_id}/{agent}/cancel  Request agent cancellation
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import AgentRun, Project, get_db
from schemas.project import AgentRunOut, AgentStatusItem

router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/agents/{project_id}/status
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/{project_id}/status",
    response_model=list[AgentStatusItem],
    summary="Get status of all agents for a project",
)
async def get_agent_statuses(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[AgentStatusItem]:
    # Ensure project exists
    proj = await db.execute(select(Project).where(Project.id == project_id))
    if proj.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Project not found")

    result = await db.execute(
        select(AgentRun)
        .where(AgentRun.project_id == project_id)
        .order_by(AgentRun.created_at)
    )
    runs = result.scalars().all()

    return [
        AgentStatusItem(
            name=run.agent_name,
            status=run.status,
            progress=100 if run.status == "complete" else (50 if run.status == "running" else 0),
            output=run.output_data,
            error=run.error_message,
            started_at=run.started_at,
            completed_at=run.completed_at,
        )
        for run in runs
    ]


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/agents/{project_id}/{agent_name}
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/{project_id}/{agent_name}",
    response_model=AgentRunOut,
    summary="Get full detail for a single agent run",
)
async def get_agent_run(
    project_id: uuid.UUID,
    agent_name: str,
    db: AsyncSession = Depends(get_db),
) -> AgentRunOut:
    result = await db.execute(
        select(AgentRun).where(
            AgentRun.project_id == project_id,
            AgentRun.agent_name == agent_name,
        )
    )
    run = result.scalar_one_or_none()
    if run is None:
        raise HTTPException(
            status_code=404,
            detail=f"No run found for agent '{agent_name}' on project {project_id}",
        )
    return AgentRunOut.model_validate(run)


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/agents/{project_id}/{agent_name}/cancel
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/{project_id}/{agent_name}/cancel",
    summary="Request cancellation of a running agent",
    status_code=status.HTTP_200_OK,
)
async def cancel_agent(
    project_id: uuid.UUID,
    agent_name: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        select(AgentRun).where(
            AgentRun.project_id == project_id,
            AgentRun.agent_name == agent_name,
        )
    )
    run = result.scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="Agent run not found")

    if run.status not in ("pending", "running"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot cancel agent in '{run.status}' state.",
        )

    # Best-effort: mark as error (actual cancellation depends on LangGraph impl)
    run.status = "error"
    run.error_message = "Cancelled by user"
    await db.flush()

    return {"message": f"Agent '{agent_name}' cancellation requested.", "status": "error"}
