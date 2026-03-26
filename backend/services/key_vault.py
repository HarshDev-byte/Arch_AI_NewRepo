"""
services/key_vault.py — Simple encrypt/decrypt helpers for storing API keys.

Uses a symmetric Fernet key derived from the VAULT_SECRET environment variable.
"""
from __future__ import annotations

import base64
import hashlib
import os
from typing import Tuple

import httpx
from cryptography.fernet import Fernet

from database import AsyncSessionLocal, APIKey, AgentKeyAssignment


def _derive_fernet_key() -> bytes:
    secret = os.getenv("VAULT_SECRET", "")
    if not secret:
        raise RuntimeError("VAULT_SECRET not configured — set in environment")
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_key(plain: str) -> str:
    f = Fernet(_derive_fernet_key())
    return f.encrypt(plain.encode("utf-8")).decode("utf-8")


def decrypt_key(enc: str) -> str:
    f = Fernet(_derive_fernet_key())
    return f.decrypt(enc.encode("utf-8")).decode("utf-8")


def preview_from_plain(plain: str) -> str:
    return plain[-4:]


def preview_key(plain_key: str) -> str:
    return "..." + plain_key[-4:] if len(plain_key) > 4 else "****"


async def test_provider_key(provider: str, key: str, timeout: int = 8) -> Tuple[bool, int | None, str | None]:
    """Perform a lightweight provider-specific check.

    Returns (ok, status_code, message).
    """
    p = (provider or "").lower()
    headers = {}
    url = None
    method = "get"

    if p in ("ollama", "local"):
        return True, None, "Local provider — no key required"

    if p == "groq":
        url = "https://api.groq.com/v1/models"
        headers = {"Authorization": f"Bearer {key}"}
    elif p in ("anthropic", "claude"):
        url = "https://api.anthropic.com/v1/models"
        headers = {"Authorization": f"Bearer {key}"}
    elif p == "mapbox":
        url = f"https://api.mapbox.com/styles/v1?access_token={key}"
    elif p in ("huggingface", "hf"):
        url = "https://huggingface.co/api/whoami-v2"
        headers = {"Authorization": f"Bearer {key}"}
    else:
        # Generic test: try a simple GET with Authorization header
        url = "https://httpbin.org/get"
        headers = {"Authorization": f"Bearer {key}"}

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.request(method, url, headers=headers)
            if resp.status_code in (200, 201):
                return True, resp.status_code, None
            if resp.status_code in (401, 403):
                return False, resp.status_code, "Unauthorized/forbidden — key invalid or insufficient permissions"
            # Other codes — return as not-ok but include message
            return False, resp.status_code, f"Unexpected status {resp.status_code}"
    except Exception as exc:
        return False, None, str(exc)


async def store_key(user_id: str, provider: str, label: str, plain_key: str) -> str:
    """Save an encrypted key using the async ORM and return the new key UUID."""
    key_enc = encrypt_key(plain_key)
    key_prev = preview_key(plain_key)
    async with AsyncSessionLocal() as db:
        k = APIKey(
            user_id=user_id,
            provider=provider,
            label=label,
            key_preview=key_prev,
            key_enc=key_enc,
        )
        db.add(k)
        await db.commit()
        return str(k.id)


async def get_key_for_agent(user_id: str, agent_name: str) -> str | None:
    """Return the decrypted API key assigned to an agent for this user.

    Falls back to environment variables when no key is stored.
    """
    async with AsyncSessionLocal() as db:
        res = await db.execute(
            """
            SELECT ak.id, ak.key_enc, ak.provider
            FROM agent_key_assignments aka
            JOIN api_keys ak ON ak.id = aka.api_key_id
            WHERE aka.user_id = :uid AND aka.agent_name = :agent AND ak.is_active = true
            """,
            {"uid": user_id, "agent": agent_name},
        )
        row = res.fetchone()
        if row:
            try:
                return decrypt_key(row[1])
            except Exception:
                return None

    # Fall back mapping to env vars
    env_map = {
        "geo":            None,
        "cost":           os.getenv("GROQ_API_KEY"),
        "layout":         os.getenv("GROQ_API_KEY"),
        "design":         os.getenv("ANTHROPIC_API_KEY") or os.getenv("GROQ_API_KEY"),
        "threed":         None,
        "vr":             None,
        "compliance":     os.getenv("GROQ_API_KEY"),
        "sustainability": os.getenv("GROQ_API_KEY"),
    }
    return env_map.get(agent_name)


async def get_provider_for_agent(user_id: str, agent_name: str) -> str:
    """Return which provider is assigned to an agent; default to free options."""
    async with AsyncSessionLocal() as db:
        res = await db.execute(
            """
            SELECT aka.provider
            FROM agent_key_assignments aka
            WHERE aka.user_id = :uid AND aka.agent_name = :agent
            """,
            {"uid": user_id, "agent": agent_name},
        )
        row = res.fetchone()
        if row and row[0]:
            return row[0]

    defaults = {
        "geo":            "openstreetmap",
        "cost":           "groq",
        "layout":         "groq",
        "design":         "groq",
        "threed":         "blender_local",
        "vr":             "babylonjs",
        "compliance":     "groq",
        "sustainability": "openmeteo",
    }
    return defaults.get(agent_name, "groq")
