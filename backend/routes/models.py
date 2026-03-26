"""
routes/models.py — 3D model generation endpoints.

Endpoints:
  POST /api/models/{project_id}          Trigger Blender .glb generation
  GET  /api/models/{project_id}          Get model status / URLs
  GET  /api/models/{project_id}/script   Preview the Blender script (debug)
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import DesignVariant, Project, get_db

router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────────────────────────────────────────

class ModelGenerationResponse(BaseModel):
    project_id: uuid.UUID
    status: str
    message: str
    variants_queued: int


class ModelStatusResponse(BaseModel):
    project_id: uuid.UUID
    variants: list[dict[str, Any]]


# ─────────────────────────────────────────────────────────────────────────────
# Background 3D task
# ─────────────────────────────────────────────────────────────────────────────

async def _generate_models_bg(project_id: uuid.UUID, floors: int) -> None:
    """Background task: generate .glb for each design variant."""
    from blender.generator import generate_all_variants
    from database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(DesignVariant).where(DesignVariant.project_id == project_id)
        )
        variants_orm = result.scalars().all()

        if not variants_orm:
            return

        # Build list of dicts for the generator
        variant_dicts = [
            {"dna": v.dna or {}, "dna_id": str(v.id), "variant_number": v.variant_number}
            for v in variants_orm
        ]

        updated = await generate_all_variants(variant_dicts, floors)

        # Write URLs back to DB
        for v_dict, v_orm in zip(updated, variants_orm):
            v_orm.model_url = v_dict.get("model_url")

        await db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/models/{project_id}
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/{project_id}",
    response_model=ModelGenerationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger Blender .glb generation for all design variants",
)
async def trigger_model_generation(
    project_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> ModelGenerationResponse:
    # Verify project exists
    proj_result = await db.execute(select(Project).where(Project.id == project_id))
    project = proj_result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    # Count variants
    var_result = await db.execute(
        select(DesignVariant).where(DesignVariant.project_id == project_id)
    )
    variants = var_result.scalars().all()
    if not variants:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No design variants found. Run /api/generate/start first.",
        )

    floors = int(project.floors or 2)
    background_tasks.add_task(_generate_models_bg, project_id, floors)

    return ModelGenerationResponse(
        project_id=project_id,
        status="queued",
        message=f"Blender model generation queued for {len(variants)} variants.",
        variants_queued=len(variants),
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/models/{project_id}
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/{project_id}",
    response_model=ModelStatusResponse,
    summary="Get 3D model generation status and URLs",
)
async def get_model_status(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ModelStatusResponse:
    result = await db.execute(
        select(DesignVariant)
        .where(DesignVariant.project_id == project_id)
        .order_by(DesignVariant.variant_number)
    )
    variants = result.scalars().all()
    if not variants:
        raise HTTPException(status_code=404, detail="No variants found for this project")

    return ModelStatusResponse(
        project_id=project_id,
        variants=[
            {
                "id":             str(v.id),
                "variant_number": v.variant_number,
                "model_url":      v.model_url,
                "thumbnail_url":  v.thumbnail_url,
                "is_selected":    v.is_selected,
                "score":          v.score,
                "model_ready":    v.model_url is not None,
            }
            for v in variants
        ],
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/models/{project_id}/script   — debug / preview
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/{project_id}/script",
    response_class=None,
    summary="Preview the Blender Python script for the best variant (debug)",
)
async def get_blender_script(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    from blender.generator import validate_script

    result = await db.execute(
        select(DesignVariant)
        .where(DesignVariant.project_id == project_id, DesignVariant.is_selected == True)
        .limit(1)
    )
    variant = result.scalar_one_or_none()
    if variant is None:
        # Fall back to variant_number=1
        result2 = await db.execute(
            select(DesignVariant)
            .where(DesignVariant.project_id == project_id)
            .order_by(DesignVariant.variant_number)
            .limit(1)
        )
        variant = result2.scalar_one_or_none()

    if variant is None:
        raise HTTPException(status_code=404, detail="No variant found")

    proj = await db.execute(select(Project).where(Project.id == project_id))
    project = proj.scalar_one_or_none()
    floors = int(getattr(project, "floors", 2) or 2)

    script = validate_script(variant.dna or {}, floors)
    return {"project_id": str(project_id), "variant_id": str(variant.id), "script": script}
