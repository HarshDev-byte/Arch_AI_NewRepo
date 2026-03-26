"""
routes/images.py — AI Image Generation API for ArchAI.

Endpoints
---------
POST /api/images/{variant_id}/generate
    Generate exterior + interior + aerial renders for a design variant.
    Uploads them to Supabase Storage, stores public URLs in DB,
    returns full result + base64 preview (for instant client display).

GET  /api/images/{variant_id}
    Return previously generated image URLs for a variant
    (fast — DB lookup only, no generation).

DELETE /api/images/{variant_id}
    Remove images from Storage + clear DB URLs (owner only).
"""

from __future__ import annotations

import base64
import logging
import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from agents.image_agent import generate_variant_images
from auth import OptionalUser, get_current_user
from config import settings
from database import DesignVariant, GeoAnalysis, Project, get_db

logger = logging.getLogger(__name__)

router = APIRouter()


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _get_variant(db: AsyncSession, variant_id: str) -> DesignVariant:
    try:
        vid = uuid.UUID(variant_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid variant_id UUID")
    result  = await db.execute(select(DesignVariant).where(DesignVariant.id == vid))
    variant = result.scalar_one_or_none()
    if variant is None:
        raise HTTPException(status_code=404, detail="Design variant not found")
    return variant


async def _get_project(db: AsyncSession, project_id: uuid.UUID) -> Project:
    result  = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


async def _get_geo(db: AsyncSession, project_id: uuid.UUID) -> dict[str, Any]:
    result = await db.execute(select(GeoAnalysis).where(GeoAnalysis.project_id == project_id))
    geo    = result.scalar_one_or_none()
    if geo is None:
        return {}
    return {
        "plot_data":        geo.plot_data        or {},
        "solar_irradiance": geo.solar_irradiance,
        "wind_data":        geo.wind_data        or {},
        "zoning_type":      geo.zoning_type,
    }


def _upload_to_supabase(path: str, img_bytes: bytes, content_type: str = "image/png") -> str | None:
    """
    Upload bytes to Supabase Storage and return the public URL.
    Returns None (and logs) on error so caller can continue gracefully.
    """
    if not settings.supabase_url or not settings.supabase_service_key:
        logger.info("images: Supabase not configured — skipping upload for %s", path)
        return None
    try:
        from supabase import create_client
        sb      = create_client(settings.supabase_url, settings.supabase_service_key)
        bucket  = settings.supabase_storage_bucket
        # upsert=True overwrites if path already exists (e.g. on regenerate)
        sb.storage.from_(bucket).upload(
            path, img_bytes,
            file_options={"content-type": content_type, "upsert": "true"},
        )
        public_url = sb.storage.from_(bucket).get_public_url(path)
        return public_url
    except Exception as exc:
        logger.warning("images: Supabase upload failed for %s: %s", path, exc)
        return None


# ─── POST /api/images/{variant_id}/generate ───────────────────────────────────

@router.post(
    "/{variant_id}/generate",
    status_code=status.HTTP_200_OK,
    summary="Generate AI architectural renders for a design variant",
)
async def generate_images(
    variant_id: str,
    user: dict | None = Depends(OptionalUser()),
    db: AsyncSession   = Depends(get_db),
):
    """
    Calls Hugging Face Inference API to build 3 renders (exterior, interior, aerial).
    Uploads to Supabase Storage and persists public URLs.
    Returns both URLs and base64 previews for instant display.

    Requires HF_API_KEY in .env (free at huggingface.co/settings/tokens).
    """
    if not settings.hf_api_key:
        raise HTTPException(
            status_code=503,
            detail=(
                "HF_API_KEY not configured. "
                "Get a free token at https://huggingface.co/settings/tokens "
                "and add it to your .env file."
            ),
        )

    variant = await _get_variant(db, variant_id)
    project = await _get_project(db, variant.project_id)
    geo_data= await _get_geo(db, variant.project_id)

    # Ownership check (soft — unauthenticated requests allowed for dev)
    if user and project.user_id and str(project.user_id) != user["user_id"]:
        raise HTTPException(status_code=403, detail="Not your project")

    dna: dict[str, Any] = variant.dna or {}
    if not dna:
        raise HTTPException(
            status_code=422,
            detail="Variant has no DNA yet. Wait for the pipeline to complete.",
        )

    # Inject floors from project so prompt builder has it
    dna_with_floors = {**dna, "floors": project.floors or 2}

    # ── Generate ──────────────────────────────────────────────────────────────
    logger.info("images: generating renders for variant %s…", variant_id)
    images = await generate_variant_images(
        dna=dna_with_floors,
        geo_data=geo_data,
        hf_api_key=settings.hf_api_key,
    )

    # ── Upload to Supabase Storage ────────────────────────────────────────────
    vid_str = str(variant.id)
    urls: dict[str, str | None] = {
        "exterior_url": None,
        "interior_url": None,
        "aerial_url":   None,
    }

    for key, label in [
        ("exterior_b64", "exterior"),
        ("interior_b64", "interior"),
        ("aerial_b64",   "aerial"),
    ]:
        b64 = images.get(key)
        if b64:
            img_bytes   = base64.b64decode(b64)
            path        = f"variants/{vid_str}/{label}.png"
            public_url  = _upload_to_supabase(path, img_bytes)
            urls[f"{label}_url"] = public_url

    # ── Persist thumbnail_url (exterior) to DB ────────────────────────────────
    thumbnail = urls.get("exterior_url")
    await db.execute(
        update(DesignVariant)
        .where(DesignVariant.id == variant.id)
        .values(thumbnail_url=thumbnail)
    )
    await db.commit()

    return {
        # Public URLs (None when Supabase not configured)
        **urls,
        # Base64 previews for instant client rendering
        "exterior_b64":    images.get("exterior_b64"),
        "interior_b64":    images.get("interior_b64"),
        "aerial_b64":      images.get("aerial_b64"),
        # Prompts (for "inspiration" display in the mood board)
        "exterior_prompt": images.get("exterior_prompt"),
        "interior_prompt": images.get("interior_prompt"),
        "aerial_prompt":   images.get("aerial_prompt"),
        # Meta
        "variant_id":      vid_str,
        "model_used":      "stabilityai/stable-diffusion-xl-base-1.0",
    }


# ─── GET /api/images/{variant_id} ─────────────────────────────────────────────

@router.get(
    "/{variant_id}",
    summary="Fetch previously generated image URLs for a variant",
)
async def get_images(
    variant_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Fast DB-only lookup — no generation."""
    variant = await _get_variant(db, variant_id)
    return {
        "variant_id":    str(variant.id),
        "thumbnail_url": variant.thumbnail_url,
        "model_url":     variant.model_url,
    }
