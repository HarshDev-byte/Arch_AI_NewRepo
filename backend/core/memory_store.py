"""
core/memory_store.py — Redis-backed Design DNA memory for ArchAI.

Responsibilities
----------------
1. **Anti-repetition**: Record every generated DNA fingerprint per user.
   The evolutionary algorithm calls ``get_seen_hashes()`` and skips any
   candidate whose fingerprint is already seen.

2. **Preference learning**: Every time a user selects a variant we call
   ``record_style_selection()``.  The function increments a sorted-set of
   style / form / material weights so future generations can be seeded
   toward the user's taste.

3. **Project result cache**: Full pipeline results are cached for 1 hour to
   make repeated GETs fast without re-running agents.

4. **Rate limiting**: Per-user sliding-window counter (default: 10 gens/hour).

5. **Graceful fallback**: When Redis is not configured (``REDIS_URL`` is
   empty) every operation silently returns safe defaults — the system
   continues working, just without persistence.  No exceptions escape.

Redis key schema
----------------
  user:{uid}:dna_history          ZSET  score=timestamp, member=sha256_hash
  user:{uid}:style_weights        ZSET  score=cumulative_weight, member=trait_value
  user:{uid}:generation_count     STRING  int — lifetime project count
  project:{pid}:result            STRING  JSON blob (TTL 1h)
  ratelimit:{uid}:generations     STRING  int (TTL 1h sliding)
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any

from config import settings

logger = logging.getLogger(__name__)

# ─── Redis connection (lazy, with fallback) ───────────────────────────────────

_pool = None


def _get_redis():
    """
    Return a Redis client, creating the connection pool on first call.
    Returns None if REDIS_URL is not configured — callers must handle None.
    """
    global _pool

    url = getattr(settings, "redis_url", "") or ""
    if not url:
        return None

    try:
        import redis.asyncio as aioredis

        if _pool is None:
            _pool = aioredis.ConnectionPool.from_url(url, decode_responses=True)
        return aioredis.Redis(connection_pool=_pool)
    except Exception as exc:
        logger.warning("Redis connection pool creation failed: %s", exc)
        return None


# ─── Anti-repetition: DNA hash history ───────────────────────────────────────

def _dna_hash(dna: dict | Any) -> str:
    """
    Stable SHA-256 fingerprint of the key DNA traits.

    Only the combination-determining attributes are hashed — numeric
    parameters like floor_height vary too gradually to be useful uniqueness
    keys, so they are intentionally excluded.
    """
    if hasattr(dna, "to_dict"):
        dna = dna.to_dict()

    key_attrs: dict[str, Any] = {
        "primary_style":          dna.get("primary_style"),
        "secondary_style":        dna.get("secondary_style"),
        "building_form":          dna.get("building_form"),
        "roof_form":              dna.get("roof_form"),
        "facade_material_palette":dna.get("facade_material_palette"),
        "facade_pattern":         dna.get("facade_pattern"),
        "window_style":           dna.get("window_style"),
        "has_courtyard":          dna.get("has_courtyard"),
    }
    canonical = json.dumps(key_attrs, sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()[:32]


async def record_generated_dna(user_id: str, dna: dict | Any) -> None:
    """
    Store a generated DNA hash so we never repeat it for this user.
    Keeps the last 200 fingerprints in a sorted set (score = UNIX timestamp).
    TTL: 90 days.
    """
    r = _get_redis()
    if r is None:
        return
    try:
        key      = f"user:{user_id}:dna_history"
        dna_hash = _dna_hash(dna)
        await r.zadd(key, {dna_hash: time.time()})
        await r.zremrangebyrank(key, 0, -201)   # keep last 200
        await r.expire(key, 60 * 60 * 24 * 90)
    except Exception as exc:
        logger.warning("record_generated_dna failed: %s", exc)
    finally:
        await r.aclose()


async def get_seen_hashes(user_id: str) -> list[str]:
    """Return all previously generated DNA fingerprints for this user."""
    r = _get_redis()
    if r is None:
        return []
    try:
        key = f"user:{user_id}:dna_history"
        return list(await r.zrange(key, 0, -1))
    except Exception as exc:
        logger.warning("get_seen_hashes failed: %s", exc)
        return []
    finally:
        await r.aclose()


async def is_dna_seen(user_id: str, dna: dict | Any) -> bool:
    """Return True if this exact DNA combination was generated before."""
    r = _get_redis()
    if r is None:
        return False
    try:
        key      = f"user:{user_id}:dna_history"
        dna_hash = _dna_hash(dna)
        score    = await r.zscore(key, dna_hash)
        return score is not None
    except Exception as exc:
        logger.warning("is_dna_seen failed: %s", exc)
        return False
    finally:
        await r.aclose()


# ─── Preference learning ──────────────────────────────────────────────────────

async def record_style_selection(user_id: str, dna: dict | Any) -> None:
    """
    When a user picks a variant, learn their preferences.
    Increments ZSET weights for each chosen trait so future DNA
    generation can be seeded toward their taste.
    """
    r = _get_redis()
    if r is None:
        return
    try:
        if hasattr(dna, "to_dict"):
            dna = dna.to_dict()

        key  = f"user:{user_id}:style_weights"
        pipe = r.pipeline()

        trait_weights = [
            (dna.get("primary_style", ""),           3),  # strongest signal
            (dna.get("secondary_style", ""),         2),
            (dna.get("building_form", ""),           2),
            (dna.get("roof_form", ""),               1),
            (dna.get("facade_material_palette", ""), 1),
            (dna.get("facade_pattern", ""),          1),
        ]
        for trait, weight in trait_weights:
            if trait:
                pipe.zincrby(key, weight, trait)

        pipe.expire(key, 60 * 60 * 24 * 365)   # 1 year
        await pipe.execute()
    except Exception as exc:
        logger.warning("record_style_selection failed: %s", exc)
    finally:
        await r.aclose()


async def get_preferred_styles(user_id: str, top_n: int = 3) -> list[str]:
    """Return the user's top ``top_n`` preferred traits (highest-weight first)."""
    r = _get_redis()
    if r is None:
        return []
    try:
        key = f"user:{user_id}:style_weights"
        return list(await r.zrevrange(key, 0, top_n - 1))
    except Exception as exc:
        logger.warning("get_preferred_styles failed: %s", exc)
        return []
    finally:
        await r.aclose()


async def get_user_style_profile(user_id: str) -> dict[str, Any]:
    """
    Full style profile consumed by the orchestrator to bias DNA seeding.

    Does NOT increment the generation counter — call ``increment_generation_count``
    separately after a successful pipeline run.
    """
    r = _get_redis()

    preferred: list[str] = []
    count_val             = 0

    if r is not None:
        try:
            preferred = await get_preferred_styles(user_id, top_n=5)

            count_key = f"user:{user_id}:generation_count"
            raw       = await r.get(count_key)
            count_val = int(raw) if raw else 0
        except Exception as exc:
            logger.warning("get_user_style_profile failed: %s", exc)
        finally:
            await r.aclose()

    return {
        "user_id":           user_id,
        "preferred_styles":  preferred,
        "generation_count":  count_val,
        "is_experienced_user": count_val >= 3,
        "top_style":         preferred[0] if preferred else None,
    }


async def increment_generation_count(user_id: str) -> int:
    """
    Increment the lifetime generation counter for this user.
    Returns the new count (0 if Redis unavailable).
    """
    r = _get_redis()
    if r is None:
        return 0
    try:
        key = f"user:{user_id}:generation_count"
        new_val = await r.incr(key)
        # No TTL — we want this to persist indefinitely
        return int(new_val)
    except Exception as exc:
        logger.warning("increment_generation_count failed: %s", exc)
        return 0
    finally:
        await r.aclose()


# ─── Project result cache ─────────────────────────────────────────────────────

async def cache_project_result(project_id: str, result: dict, ttl: int = 3_600) -> None:
    """Cache the full pipeline result (JSON) for fast re-fetching. Default TTL: 1 hour."""
    r = _get_redis()
    if r is None:
        return
    try:
        key  = f"project:{project_id}:result"
        blob = json.dumps(result, default=str)
        await r.setex(key, ttl, blob)
    except Exception as exc:
        logger.warning("cache_project_result failed: %s", exc)
    finally:
        await r.aclose()


async def get_cached_project(project_id: str) -> dict | None:
    """Return the cached pipeline result or None if not yet cached / expired."""
    r = _get_redis()
    if r is None:
        return None
    try:
        data = await r.get(f"project:{project_id}:result")
        return json.loads(data) if data else None
    except Exception as exc:
        logger.warning("get_cached_project failed: %s", exc)
        return None
    finally:
        await r.aclose()


async def invalidate_project_cache(project_id: str) -> None:
    """Delete the cached result for a project (e.g. on re-generation)."""
    r = _get_redis()
    if r is None:
        return
    try:
        await r.delete(f"project:{project_id}:result")
    except Exception as exc:
        logger.warning("invalidate_project_cache failed: %s", exc)
    finally:
        await r.aclose()


# ─── Rate limiting ────────────────────────────────────────────────────────────

async def check_rate_limit(
    user_id: str,
    max_per_hour: int = 10,
) -> tuple[bool, int]:
    """
    Sliding-window rate limiter (1-hour window).

    Returns
    -------
    (is_allowed, info)
        is_allowed=True  → ``info`` is the remaining quota for this window
        is_allowed=False → ``info`` is the seconds until the window resets
    """
    r = _get_redis()
    if r is None:
        # Redis unavailable — allow everything
        return True, max_per_hour

    key = f"ratelimit:{user_id}:generations"
    try:
        current = await r.get(key)

        if current is None:
            # First request in this window
            await r.setex(key, 3_600, 1)
            return True, max_per_hour - 1

        count = int(current)
        if count >= max_per_hour:
            ttl = await r.ttl(key)
            return False, max(0, ttl)   # seconds until reset

        await r.incr(key)
        return True, max_per_hour - count - 1

    except Exception as exc:
        logger.warning("check_rate_limit failed: %s — allowing request", exc)
        return True, max_per_hour
    finally:
        await r.aclose()


# ─── Legacy compat — used by orchestrator's get_store() call ─────────────────

class _MemoryStoreCompat:
    """
    Thin wrapper that satisfies the ``memory.get_all()`` / ``memory.record()``
    interface used by the design node in orchestrator.py.
    """

    def __init__(self, user_id: str) -> None:
        self._user_id = user_id
        self._local_cache: list[str] = []

    async def get_all(self) -> list[str]:
        hashes = await get_seen_hashes(self._user_id)
        self._local_cache = hashes
        return hashes

    async def record(self, fingerprint: str) -> None:
        # Store as a pseudo-DNA dict with just the fingerprint as primary_style
        # so _dna_hash produces a unique value
        pseudo = {"primary_style": fingerprint}
        await record_generated_dna(self._user_id, pseudo)


async def get_store(project_id: str, user_id: str | None = None) -> _MemoryStoreCompat:
    """
    Factory used by orchestrator.py::

        memory = await get_store(state["project_id"], state.get("user_id"))
        prior  = await memory.get_all()
        ...
        await memory.record(ind["dna"].fingerprint())

    Falls back to ``project_id`` as the user namespace when no ``user_id``
    is available (anonymous sessions).
    """
    return _MemoryStoreCompat(user_id or project_id)
