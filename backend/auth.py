"""
backend/auth.py — Supabase JWT verification for FastAPI.

Usage
-----
  from auth import get_current_user, OptionalUser

  # Protected endpoint — raises 401 if token invalid/missing
  @router.get("/protected")
  async def handler(user: dict = Depends(get_current_user)):
      return {"user_id": user["user_id"]}

  # Optional auth — user is None when no token is present
  @router.get("/public")
  async def handler(user: dict | None = Depends(OptionalUser())):
      ...

Token payload returned as:
  {
    "user_id": "uuid-string",       # Supabase auth.uid()
    "email":   "user@example.com",
    "role":    "authenticated",
  }
"""

from __future__ import annotations

import logging
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from config import settings

logger = logging.getLogger(__name__)

# ─── Security scheme ─────────────────────────────────────────────────────────

_bearer = HTTPBearer(auto_error=False)   # auto_error=False → we handle 401 ourselves


# ─── Core verifier ───────────────────────────────────────────────────────────

def _decode_token(token: str) -> dict:
    """
    Decode and verify a Supabase JWT.

    Supabase signs JWTs with the project's JWT secret (HS256).
    Retrieve it from: Supabase Dashboard → Settings → API → JWT Secret.

    Falls back to a permissive decode (no signature check) when the secret
    is not configured — **never do this in production**.
    """
    if not settings.supabase_jwt_secret:
        logger.warning(
            "SUPABASE_JWT_SECRET not set — decoding JWT without signature verification. "
            "Set it in .env for production."
        )
        payload = jwt.decode(
            token,
            options={"verify_signature": False},
            algorithms=["HS256"],
        )
    else:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise ValueError("Token has no 'sub' claim")

    return {
        "user_id": user_id,
        "email":   payload.get("email", ""),
        "role":    payload.get("role", "authenticated"),
        "raw":     payload,
    }


# ─── FastAPI dependency — required auth ───────────────────────────────────────

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> dict:
    """
    FastAPI dependency.  Raises HTTP 401 when no valid Bearer token is present.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return _decode_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as exc:
        logger.exception("Unexpected auth error")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        )


# ─── FastAPI dependency — optional auth ──────────────────────────────────────

class OptionalUser:
    """
    Dependency that returns the decoded user dict OR None.

    Use for endpoints that adjust behaviour based on authentication
    without hard-requiring it (e.g. rate-limiting, personalisation).

    Example::

        @router.get("/feed")
        async def feed(user: dict | None = Depends(OptionalUser())):
            if user:
                return personalised_feed(user["user_id"])
            return public_feed()
    """

    async def __call__(
        self,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    ) -> Optional[dict]:
        if credentials is None:
            return None
        try:
            return _decode_token(credentials.credentials)
        except Exception:
            return None


# ─── Owner check helper ───────────────────────────────────────────────────────

def assert_owner(project_user_id, current_user: dict) -> None:
    """
    Raise HTTP 403 when *current_user* is not the owner of a project.

    ``project_user_id`` can be a uuid.UUID or str.
    """
    import uuid as _uuid
    pid    = str(project_user_id)
    uid    = str(current_user["user_id"])
    if pid != uid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to modify this project",
        )
