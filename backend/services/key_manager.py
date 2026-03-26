"""
services/key_manager.py — Resolve per-user per-agent provider & decrypted key.

Returns a tuple (provider, api_key_or_none). If no assignment exists, falls back
to sensible defaults based on config settings.
"""
from __future__ import annotations

from typing import Tuple
import asyncio

from sqlalchemy import select

from config import settings
from database import AsyncSessionLocal, AgentKeyAssignment, APIKey
from services.key_vault import decrypt_key


async def get_provider_and_key(user_id: str | None, agent_name: str) -> Tuple[str | None, str | None]:
    """Return (provider, key) for this user+agent if present, else fallbacks.

    If user_id is None or no assignment found, returns provider based on
    sensible defaults (may return None for key when provider is a free/local provider).
    """
    # 1) If user provided an assignment, try to resolve it
    if user_id:
        async with AsyncSessionLocal() as db:
            r = await db.execute(select(AgentKeyAssignment).where(
                AgentKeyAssignment.user_id == user_id,
                AgentKeyAssignment.agent_name == agent_name,
            ))
            assign = r.scalar_one_or_none()
            if assign:
                provider = assign.provider
                if assign.api_key_id:
                    r2 = await db.execute(select(APIKey).where(APIKey.id == assign.api_key_id))
                    ak = r2.scalar_one_or_none()
                    if ak:
                        try:
                            return provider, decrypt_key(ak.key_enc)
                        except Exception:
                            return provider, None
                return provider, None

    # 2) No user assignment — fall back to global settings per agent
    a = agent_name.lower()
    if a in ("chat", "design"):
        # Prefer Anthropic -> Groq -> Ollama
        if settings.anthropic_api_key:
            return "anthropic", settings.anthropic_api_key
        if settings.groq_api_key:
            return "groq", settings.groq_api_key
        return "ollama", None
    if a == "geo":
        return "openstreetmap", None
    if a == "images":
        if settings.hf_api_key:
            return "huggingface", settings.hf_api_key
        return "huggingface", None
    # Default: try groq then anthropic then local
    if settings.groq_api_key:
        return "groq", settings.groq_api_key
    if settings.anthropic_api_key:
        return "anthropic", settings.anthropic_api_key
    return "ollama", None
