"""
core/vector_memory.py — Qdrant-backed semantic design memory for ArchAI.

Responsibilities
----------------
1. **Semantic search**: Find past designs similar to a natural-language query
   using sentence-transformer embeddings.
2. **Design storage**: Persist completed designs (DNA + summary + score) as
   vector points so the evolutionary engine can learn from history.
3. **User scoping**: Every vector is tagged with user_id for privacy isolation.
4. **Graceful fallback**: If Qdrant is not configured, all operations log a
   warning and return empty results. The system keeps working.

Setup
-----
Option A — Qdrant Cloud (recommended):
    pip install qdrant-client sentence-transformers
    Set QDRANT_URL and QDRANT_API_KEY in .env

Option B — Local Docker:
    docker run -p 6333:6333 qdrant/qdrant
    Set QDRANT_URL=http://localhost:6333 (no API key needed)

Collection: archai_designs
  - Vector size: 384 (all-MiniLM-L6-v2)
  - Distance: Cosine
"""
from __future__ import annotations

import hashlib
import json
import logging
import uuid
from typing import Any

logger = logging.getLogger(__name__)

# ─── Lazy singletons ─────────────────────────────────────────────────────────

_qdrant_client = None
_embedder = None
_COLLECTION = "archai_designs"
_VECTOR_DIM = 384


def _get_client():
    """Return Qdrant client, creating it on first call. Returns None if unconfigured."""
    global _qdrant_client
    if _qdrant_client is not None:
        return _qdrant_client

    try:
        from config import settings
        url = getattr(settings, "qdrant_url", "") or ""
        api_key = getattr(settings, "qdrant_api_key", "") or ""

        if not url:
            return None

        from qdrant_client import QdrantClient
        if api_key:
            _qdrant_client = QdrantClient(url=url, api_key=api_key)
        else:
            _qdrant_client = QdrantClient(url=url)

        _ensure_collection(_qdrant_client)
        return _qdrant_client

    except ImportError:
        logger.warning(
            "qdrant-client not installed. Run: pip install qdrant-client sentence-transformers"
        )
        return None
    except Exception as exc:
        logger.warning("Qdrant connection failed: %s", exc)
        return None


def _ensure_collection(client) -> None:
    """Create the designs collection if it does not exist."""
    from qdrant_client.models import Distance, VectorParams
    existing = {c.name for c in client.get_collections().collections}
    if _COLLECTION not in existing:
        client.create_collection(
            collection_name=_COLLECTION,
            vectors_config=VectorParams(size=_VECTOR_DIM, distance=Distance.COSINE),
        )
        logger.info("Created Qdrant collection: %s", _COLLECTION)


def _get_embedder():
    """Return sentence-transformer model (loaded once)."""
    global _embedder
    if _embedder is not None:
        return _embedder
    try:
        from sentence_transformers import SentenceTransformer
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
        return _embedder
    except ImportError:
        logger.warning(
            "sentence-transformers not installed. Run: pip install sentence-transformers"
        )
        return None
    except Exception as exc:
        logger.warning("Embedder load failed: %s", exc)
        return None


def _embed(text: str) -> list[float] | None:
    """Convert text to a 384-dim embedding. Returns None on failure."""
    embedder = _get_embedder()
    if embedder is None:
        return None
    try:
        vector = embedder.encode(text, normalize_embeddings=True).tolist()
        return vector
    except Exception as exc:
        logger.warning("Embedding failed: %s", exc)
        return None


def _design_to_text(design_summary: str, dna: dict) -> str:
    """
    Convert a design into a rich text string for embedding.
    Combines the free-text summary with key DNA traits.
    """
    traits = [
        dna.get("primary_style", ""),
        dna.get("secondary_style", ""),
        dna.get("building_form", ""),
        dna.get("roof_form", ""),
        dna.get("facade_material_palette", ""),
        dna.get("facade_pattern", ""),
        dna.get("window_style", ""),
    ]
    trait_str = " ".join(t for t in traits if t)
    return f"{design_summary} {trait_str}".strip()


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

async def store_design(
    project_id: str,
    design_summary: str,
    dna: dict,
    score: float,
    user_id: str | None = None,
) -> str:
    """
    Embed and store a design in Qdrant.

    Returns the UUID vector point ID, or empty string on failure.
    """
    client = _get_client()
    if client is None:
        return ""

    text = _design_to_text(design_summary, dna)
    vector = _embed(text)
    if vector is None:
        return ""

    point_id = str(uuid.uuid4())
    payload: dict[str, Any] = {
        "project_id":      project_id,
        "user_id":         user_id or "anonymous",
        "design_summary":  design_summary,
        "score":           score,
        "primary_style":   dna.get("primary_style"),
        "secondary_style": dna.get("secondary_style"),
        "building_form":   dna.get("building_form"),
        "roof_form":       dna.get("roof_form"),
        "dna_json":        json.dumps(dna, default=str),
    }

    try:
        from qdrant_client.models import PointStruct
        client.upsert(
            collection_name=_COLLECTION,
            points=[PointStruct(id=point_id, vector=vector, payload=payload)],
        )
        logger.info("Stored design %s for user %s", point_id, user_id)
        return point_id
    except Exception as exc:
        logger.warning("store_design failed: %s", exc)
        return ""


async def query_designs(
    query: str,
    top_k: int = 5,
    user_id: str | None = None,
    score_threshold: float = 0.3,
) -> list[dict[str, Any]]:
    """
    Semantic search for past designs similar to the given natural-language query.

    Args:
        query: Free-text description e.g. "modern courtyard house with solar panels"
        top_k: Max results to return.
        user_id: If set, filter to this user's designs only.
        score_threshold: Minimum cosine similarity (0–1).

    Returns list of dicts with design metadata and similarity score.
    """
    client = _get_client()
    if client is None:
        return []

    vector = _embed(query)
    if vector is None:
        return []

    try:
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        search_filter = None
        if user_id:
            search_filter = Filter(
                must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]
            )

        hits = client.search(
            collection_name=_COLLECTION,
            query_vector=vector,
            limit=top_k,
            score_threshold=score_threshold,
            query_filter=search_filter,
            with_payload=True,
        )

        results = []
        for hit in hits:
            payload = hit.payload or {}
            results.append({
                "vector_id":      str(hit.id),
                "similarity":     round(hit.score, 4),
                "project_id":     payload.get("project_id"),
                "user_id":        payload.get("user_id"),
                "design_summary": payload.get("design_summary"),
                "primary_style":  payload.get("primary_style"),
                "secondary_style":payload.get("secondary_style"),
                "building_form":  payload.get("building_form"),
                "score":          payload.get("score"),
            })

        return results

    except Exception as exc:
        logger.warning("query_designs failed: %s", exc)
        return []


async def delete_user_designs(user_id: str) -> int:
    """
    Delete all design vectors for a user (GDPR / account deletion).
    Returns the number of points deleted.
    """
    client = _get_client()
    if client is None:
        return 0

    try:
        from qdrant_client.models import Filter, FieldCondition, MatchValue, FilterSelector
        result = client.delete(
            collection_name=_COLLECTION,
            points_selector=FilterSelector(
                filter=Filter(
                    must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]
                )
            ),
        )
        logger.info("Deleted designs for user %s", user_id)
        return getattr(result, "deleted_count", 0)
    except Exception as exc:
        logger.warning("delete_user_designs failed: %s", exc)
        return 0


async def get_collection_stats() -> dict[str, Any]:
    """Return stats about the vector memory collection (for health checks)."""
    client = _get_client()
    if client is None:
        return {"status": "unconfigured", "count": 0}

    try:
        info = client.get_collection(_COLLECTION)
        return {
            "status":       "connected",
            "collection":   _COLLECTION,
            "vector_count": info.points_count,
            "vector_dim":   _VECTOR_DIM,
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc)}
