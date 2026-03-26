"""
routes/chat.py — Design Chat API for ArchAI.

Endpoints
---------
POST /api/chat/{project_id}/message   Send a natural-language design command
GET  /api/chat/{project_id}/history   Fetch stored chat history for a project
DELETE /api/chat/{project_id}/history Clear chat history

Flow
----
1. Resolve project + selected variant (auth-checked).
2. Fetch current DNA from design_variants row.
3. Call chat_agent.interpret_design_command() → LLM → structured mutations.
4. Apply mutations to DNA with chat_agent.apply_dna_mutations().
5. Selectively re-run only the affected agents (layout / compliance / sustainability).
6. Persist the mutated DNA back to the design_variants row.
7. Append message pair to the project's Redis chat history (TTL 7 days).
8. Return explanation + updated DNA + agent results.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from agents.chat_agent import apply_dna_mutations, interpret_design_command
from agents.compliance_agent import check_compliance
from agents.layout_agent import generate_layout
from agents.sustainability_agent import analyze_sustainability
from auth import OptionalUser, get_current_user
from database import DesignVariant, GeoAnalysis, Project, get_db

logger = logging.getLogger(__name__)

router = APIRouter()


# ─── Pydantic models ──────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message:    str
    variant_id: str     # UUID of the DesignVariant to mutate


class ChatResponse(BaseModel):
    explanation:       str
    intent:            str
    updated_dna:       dict[str, Any]
    mutations_applied: dict[str, Any]
    agents_rerun:      list[str]
    agent_results:     dict[str, Any]
    variant_id:        str


# ─── Internal helpers ─────────────────────────────────────────────────────────

async def _fetch_project(
    db: AsyncSession,
    project_id: str,
    user: dict | None,
) -> Project:
    """Load project, enforce ownership."""
    try:
        pid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project_id UUID")

    result  = await db.execute(select(Project).where(Project.id == pid))
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    # Owner check (skip for unauthenticated / anonymous projects)
    if user and project.user_id and str(project.user_id) != user["user_id"]:
        raise HTTPException(status_code=403, detail="Not your project")

    return project


async def _fetch_variant(
    db: AsyncSession,
    variant_id: str,
    project_id: str,
) -> DesignVariant:
    """Load and validate a design variant belongs to the project."""
    try:
        vid = uuid.UUID(variant_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid variant_id UUID")

    result  = await db.execute(select(DesignVariant).where(DesignVariant.id == vid))
    variant = result.scalar_one_or_none()
    if variant is None:
        raise HTTPException(status_code=404, detail="Design variant not found")
    if str(variant.project_id) != project_id:
        raise HTTPException(status_code=403, detail="Variant does not belong to this project")

    return variant


async def _fetch_geo(db: AsyncSession, project_id: str) -> dict[str, Any]:
    """Return GeoAnalysis columns as a plain dict (empty dict if no geo record)."""
    try:
        pid = uuid.UUID(project_id)
    except ValueError:
        return {}

    result = await db.execute(select(GeoAnalysis).where(GeoAnalysis.project_id == pid))
    geo    = result.scalar_one_or_none()
    if geo is None:
        return {}

    return {
        "latitude":            float(geo.project.latitude)   if geo.project else 0.0,
        "longitude":           float(geo.project.longitude)  if geo.project else 0.0,
        "fsi_allowed":         geo.fsi_allowed,
        "plot_data":           geo.plot_data   or {},
        "solar_irradiance":    geo.solar_irradiance,
        "wind_data":           geo.wind_data   or {},
        "zoning_type":         geo.zoning_type,
    }


_REDIS_CHAT_TTL = 60 * 60 * 24 * 7   # 7 days


async def _append_chat_history(
    project_id: str,
    user_msg: str,
    assistant_msg: str,
    mutations: dict,
) -> None:
    """Append the exchange to Redis chat history (best-effort, no exception propagation)."""
    try:
        from core.memory_store import _get_redis
        r = _get_redis()
        if r is None:
            return
        key   = f"project:{project_id}:chat_history"
        entry = json.dumps({
            "ts":       datetime.now(timezone.utc).isoformat(),
            "user":     user_msg,
            "assistant":assistant_msg,
            "mutations":mutations,
        })
        await r.rpush(key, entry)
        await r.expire(key, _REDIS_CHAT_TTL)
        await r.aclose()
    except Exception as exc:
        logger.warning("Failed to append chat history: %s", exc)


# ─── POST /api/chat/{project_id}/message ─────────────────────────────────────

@router.post(
    "/{project_id}/message",
    response_model=ChatResponse,
    summary="Send a natural-language design command",
)
async def design_chat(
    project_id: str,
    body: ChatRequest,
    user: dict | None = Depends(OptionalUser()),
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    """
    Interpret a natural language command, mutate the Design DNA,
    selectively re-run agents, and persist the result.
    """
    # ── 1. Load project + variant ─────────────────────────────────────────────
    project = await _fetch_project(db, project_id, user)
    variant = await _fetch_variant(db, body.variant_id, project_id)

    current_dna: dict[str, Any] = variant.dna or {}
    if not current_dna:
        raise HTTPException(
            status_code=422,
            detail="This variant has no DNA data yet. Wait for the pipeline to complete.",
        )

    project_context = {
        "floors":        project.floors        or 2,
        "budget_inr":    project.budget_inr    or 0,
        "plot_area_sqm": project.plot_area_sqm or 100.0,
    }

    # ── 2. Interpret command ──────────────────────────────────────────────────
    try:
        uid = user["user_id"] if user else None
        mutations = await interpret_design_command(
            user_message=body.message,
            current_dna=current_dna,
            project_context=project_context,
            user_id=uid,
        )
    except Exception as exc:
        logger.error("Chat agent error: %s", exc)
        raise HTTPException(status_code=502, detail=f"AI chat agent error: {exc}")

    updated_dna = await apply_dna_mutations(current_dna, mutations)

    # ── 3. Selectively re-run agents ──────────────────────────────────────────
    agents_to_rerun: list[str] = mutations.get("agents_to_rerun") or []
    agent_results:   dict[str, Any] = {}

    if mutations.get("intent") == "rerun_full":
        agents_to_rerun = ["layout", "compliance", "sustainability"]

    geo_data: dict[str, Any] = {}
    if agents_to_rerun:
        geo_data = await _fetch_geo(db, project_id)
        # enrich with project lat/lon if geo record doesn't have them
        if not geo_data.get("latitude"):
            geo_data["latitude"]  = float(project.latitude  or 0)
            geo_data["longitude"] = float(project.longitude or 0)

    if "layout" in agents_to_rerun:
        try:
            agent_results["layout"] = await generate_layout(
                plot_area_sqm=float(project.plot_area_sqm or 100),
                floors=int(project.floors or 2),
                budget_inr=int(project.budget_inr or 5_000_000),
                design_dna=updated_dna,
                geo_data=geo_data,
            )
        except Exception as exc:
            logger.warning("Layout re-run failed: %s", exc)
            agent_results["layout"] = {"error": str(exc)}

    if "compliance" in agents_to_rerun:
        try:
            agent_results["compliance"] = await check_compliance(
                plot_area_sqm=float(project.plot_area_sqm or 100),
                floors=int(project.floors or 2),
                design_dna=updated_dna,
                geo_data=geo_data,
            )
        except Exception as exc:
            logger.warning("Compliance re-run failed: %s", exc)
            agent_results["compliance"] = {"error": str(exc)}

    if "sustainability" in agents_to_rerun:
        try:
            agent_results["sustainability"] = await analyze_sustainability(
                latitude=float(project.latitude   or 0),
                longitude=float(project.longitude or 0),
                plot_area_sqm=float(project.plot_area_sqm or 100),
                floors=int(project.floors or 2),
                design_dna=updated_dna,
                geo_data=geo_data,
            )
        except Exception as exc:
            logger.warning("Sustainability re-run failed: %s", exc)
            agent_results["sustainability"] = {"error": str(exc)}

    # ── 4. Persist mutated DNA ────────────────────────────────────────────────
    await db.execute(
        update(DesignVariant)
        .where(DesignVariant.id == variant.id)
        .values(dna=updated_dna)
    )
    await db.commit()

    # ── 5. Append to Redis chat history (best-effort) ─────────────────────────
    explanation = mutations.get("explanation") or "Design updated."
    await _append_chat_history(
        project_id=project_id,
        user_msg=body.message,
        assistant_msg=explanation,
        mutations=mutations.get("dna_mutations") or {},
    )

    return ChatResponse(
        explanation=explanation,
        intent=mutations.get("intent", "modify_style"),
        updated_dna=updated_dna,
        mutations_applied=mutations.get("dna_mutations") or {},
        agents_rerun=agents_to_rerun,
        agent_results=agent_results,
        variant_id=body.variant_id,
    )


# ─── GET /api/chat/{project_id}/history ──────────────────────────────────────

@router.get(
    "/{project_id}/history",
    summary="Fetch stored chat history for a project (most recent 50 messages)",
)
async def get_chat_history(
    project_id: str,
    limit: int = 50,
    user: dict | None = Depends(OptionalUser()),
    db: AsyncSession = Depends(get_db),
):
    # Light ownership check
    await _fetch_project(db, project_id, user)

    try:
        from core.memory_store import _get_redis
        r = _get_redis()
        if r is None:
            return {"history": [], "redis_enabled": False}

        key     = f"project:{project_id}:chat_history"
        entries = await r.lrange(key, -limit, -1)   # latest N
        await r.aclose()

        history = []
        for entry in entries:
            try:
                history.append(json.loads(entry))
            except json.JSONDecodeError:
                pass

        return {"history": history, "redis_enabled": True}
    except Exception as exc:
        logger.warning("get_chat_history Redis error: %s", exc)
        return {"history": [], "error": str(exc)}


# ─── DELETE /api/chat/{project_id}/history ────────────────────────────────────

@router.delete(
    "/{project_id}/history",
    status_code=status.HTTP_200_OK,
    summary="Clear chat history for a project",
)
async def clear_chat_history(
    project_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _fetch_project(db, project_id, user)
    # Only owner can clear
    if project.user_id and str(project.user_id) != user["user_id"]:
        raise HTTPException(status_code=403, detail="Only the project owner can clear chat history")

    try:
        from core.memory_store import _get_redis
        r = _get_redis()
        if r:
            await r.delete(f"project:{project_id}:chat_history")
            await r.aclose()
        return {"status": "cleared", "project_id": project_id}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Redis error: {exc}")
