"""
backend/routes/memory.py — Vector Memory & Style Profile API routes

Endpoints:
  POST /api/memory/search           — semantic search in design vector store
  POST /api/memory/store            — store a design in vector memory
  GET  /api/memory/stats            — collection health & count
  GET  /api/memory/profile/{uid}    — user style preference profile
  DELETE /api/memory/user/{uid}     — GDPR delete all user vectors
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()


# ─── Schemas ─────────────────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str = Field(..., description="Natural-language design description")
    top_k: int = Field(5, ge=1, le=20)
    user_id: str | None = None


class StoreRequest(BaseModel):
    project_id: str
    design_summary: str
    dna: dict
    score: float = 0.0
    user_id: str | None = None


# ─── Routes ──────────────────────────────────────────────────────────────────

@router.post("/search")
async def search_designs(req: SearchRequest):
    """Semantic search for similar past architectural designs."""
    try:
        from core.vector_memory import query_designs
        results = await query_designs(
            query=req.query,
            top_k=req.top_k,
            user_id=req.user_id,
        )
        return {"query": req.query, "results": results, "count": len(results)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/store")
async def store_design(req: StoreRequest):
    """Store a completed design in the vector memory."""
    try:
        from core.vector_memory import store_design as _store
        vector_id = await _store(
            project_id=req.project_id,
            design_summary=req.design_summary,
            dna=req.dna,
            score=req.score,
            user_id=req.user_id,
        )
        return {"status": "stored", "vector_id": vector_id}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/stats")
async def memory_stats():
    """Return vector memory collection statistics."""
    try:
        from core.vector_memory import get_collection_stats
        return await get_collection_stats()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/profile/{user_id}")
async def user_style_profile(user_id: str):
    """Return a user's learned style preference profile."""
    try:
        from core.memory_store import get_user_style_profile
        return await get_user_style_profile(user_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/user/{user_id}")
async def delete_user_memory(user_id: str):
    """Delete all vector memory entries for a user (GDPR)."""
    try:
        from core.vector_memory import delete_user_designs
        deleted = await delete_user_designs(user_id)
        return {"status": "deleted", "user_id": user_id, "deleted_count": deleted}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
