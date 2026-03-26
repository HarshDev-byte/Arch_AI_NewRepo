"""
routes/users.py — User profile and style preferences API.

Endpoints
---------
GET  /api/users/me                     Current user profile (from JWT)
GET  /api/users/me/style-profile       Redis-backed style preferences + generation count
POST /api/users/me/select-variant      Record a variant selection (preference learning)
DELETE /api/users/me/style-profile     Reset learned preferences
GET  /api/users/me/rate-limit          Check remaining generation quota
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from auth import get_current_user
from core.memory_store import (
    check_rate_limit,
    get_seen_hashes,
    get_user_style_profile,
    record_style_selection,
)
from config import settings

router = APIRouter()


# ─── GET /api/users/me ────────────────────────────────────────────────────────

@router.get("/me", summary="Current user info (from JWT)")
async def get_me(user: dict = Depends(get_current_user)):
    return {
        "user_id": user["user_id"],
        "email":   user["email"],
        "role":    user["role"],
    }


# ─── GET /api/users/me/style-profile ─────────────────────────────────────────

@router.get(
    "/me/style-profile",
    summary="Learned style preferences for this user",
)
async def get_style_profile(user: dict = Depends(get_current_user)):
    """
    Returns the Redis-backed style taste profile:

    ```json
    {
      "user_id": "...",
      "preferred_styles":  ["tropical_modern", "biophilic_organic"],
      "generation_count":  7,
      "is_experienced_user": true,
      "top_style": "tropical_modern",
      "seen_dna_count": 35
    }
    ```
    """
    uid     = user["user_id"]
    profile = await get_user_style_profile(uid)
    hashes  = await get_seen_hashes(uid)

    return {
        **profile,
        "seen_dna_count": len(hashes),
        "redis_enabled":  bool(getattr(settings, "redis_url", "")),
    }


# ─── POST /api/users/me/select-variant ───────────────────────────────────────

class SelectVariantRequest(BaseModel):
    dna: dict   # Full DNA dict from a DesignVariant


@router.post(
    "/me/select-variant",
    summary="Record a variant selection for preference learning",
    status_code=status.HTTP_200_OK,
)
async def select_variant(
    body: SelectVariantRequest,
    user: dict = Depends(get_current_user),
):
    """
    Called when a user clicks "Use this design" on a variant card.
    Increments weighted style ZSET in Redis so future generations
    are biased toward their taste.
    """
    await record_style_selection(user["user_id"], body.dna)
    return {"status": "recorded", "user_id": user["user_id"]}


# ─── DELETE /api/users/me/style-profile ──────────────────────────────────────

@router.delete(
    "/me/style-profile",
    summary="Reset learned style preferences",
    status_code=status.HTTP_200_OK,
)
async def reset_style_profile(user: dict = Depends(get_current_user)):
    """
    Clears all style weights and DNA history for this user.
    Useful for a 'fresh start'.
    """
    from core.memory_store import _get_redis

    r = _get_redis()
    if r is None:
        return {"status": "no_op", "reason": "Redis not configured"}

    try:
        uid = user["user_id"]
        await r.delete(
            f"user:{uid}:style_weights",
            f"user:{uid}:dna_history",
            f"user:{uid}:generation_count",
        )
        return {"status": "reset", "user_id": uid}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Redis error: {exc}")
    finally:
        await r.aclose()


# ─── GET /api/users/me/rate-limit ─────────────────────────────────────────────

@router.get(
    "/me/rate-limit",
    summary="Check remaining generation quota for this hour",
)
async def get_rate_limit(user: dict = Depends(get_current_user)):
    """
    Returns remaining quota and whether the user is currently allowed.

    ```json
    {
      "allowed": true,
      "remaining": 7,
      "max_per_hour": 10,
      "reset_in_seconds": null
    }
    ```
    """
    max_per_hour = 10   # TODO: vary by subscription tier
    allowed, info = await check_rate_limit(user["user_id"], max_per_hour)

    return {
        "allowed":           allowed,
        "remaining":         info if allowed else 0,
        "max_per_hour":      max_per_hour,
        "reset_in_seconds":  None if allowed else info,
    }
