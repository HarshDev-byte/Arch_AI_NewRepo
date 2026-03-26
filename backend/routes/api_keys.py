"""routes/api_keys.py — Manage encrypted API keys and per-agent assignments.

Endpoints (authenticated):
- GET  /api/users/me/api-keys          -> list keys
- POST /api/users/me/api-keys          -> add key (encrypts server-side)
- POST /api/users/me/api-keys/{id}/test -> test key and update last_tested/test_ok
- DELETE /api/users/me/api-keys/{id}   -> delete key

- GET  /api/users/me/assignments      -> list per-agent assignments
- PUT  /api/users/me/assignments      -> upsert assignment for an agent

"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, insert, update, delete

from auth import get_current_user
from database import AsyncSessionLocal, APIKey, AgentKeyAssignment, get_db
from services.key_vault import encrypt_key, decrypt_key, preview_from_plain, test_provider_key
from services.gemini_client import get_key_status

router = APIRouter()


class CreateKeyRequest(BaseModel):
    provider: str
    label: str
    key: str


class AssignmentRequest(BaseModel):
    agent_name: str
    provider: str
    api_key_id: str | None = None


@router.get("/me/api-keys")
async def list_my_keys(current_user: dict = Depends(get_current_user)):
    uid = current_user["user_id"]
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(APIKey).where(APIKey.user_id == uid))
        keys = res.scalars().all()
        out = [
            {
                "id": str(k.id),
                "provider": k.provider,
                "label": k.label,
                "key_preview": k.key_preview,
                "is_active": k.is_active,
                "last_tested": k.last_tested.isoformat() if k.last_tested else None,
                "test_ok": k.test_ok,
                "created_at": k.created_at.isoformat() if k.created_at else None,
            }
            for k in keys
        ]
        return out


@router.post("/me/api-keys", status_code=201)
async def create_key(body: CreateKeyRequest, current_user: dict = Depends(get_current_user)):
    uid = current_user["user_id"]
    enc = encrypt_key(body.key)
    preview = preview_from_plain(body.key)
    async with AsyncSessionLocal() as db:
        new = APIKey(
            user_id=uid,
            provider=body.provider,
            label=body.label,
            key_preview=preview,
            key_enc=enc,
        )
        db.add(new)
        await db.commit()
        return {"id": str(new.id), "provider": new.provider, "label": new.label, "key_preview": new.key_preview}


@router.post("/me/api-keys/{key_id}/test")
async def test_key(key_id: str, current_user: dict = Depends(get_current_user)):
    uid = current_user["user_id"]
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(APIKey).where(APIKey.id == key_id, APIKey.user_id == uid))
        key = res.scalar_one_or_none()
        if key is None:
            raise HTTPException(status_code=404, detail="Key not found")
        try:
            plain = decrypt_key(key.key_enc)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Unable to decrypt key: {exc}")
        ok, status_code, msg = await test_provider_key(key.provider, plain)
        key.last_tested = datetime.now(timezone.utc)
        key.test_ok = bool(ok)
        await db.commit()
        return {"ok": ok, "status_code": status_code, "message": msg}


@router.delete("/me/api-keys/{key_id}", status_code=204)
async def delete_key(key_id: str, current_user: dict = Depends(get_current_user)):
    uid = current_user["user_id"]
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(APIKey).where(APIKey.id == key_id, APIKey.user_id == uid))
        key = res.scalar_one_or_none()
        if key is None:
            raise HTTPException(status_code=404, detail="Key not found")
        await db.delete(key)
        await db.commit()
        return {}


@router.get("/me/assignments")
async def list_assignments(current_user: dict = Depends(get_current_user)):
    uid = current_user["user_id"]
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(AgentKeyAssignment).where(AgentKeyAssignment.user_id == uid))
        assigns = res.scalars().all()
        out = [
            {"id": str(a.id), "agent_name": a.agent_name, "provider": a.provider, "api_key_id": str(a.api_key_id) if a.api_key_id else None}
            for a in assigns
        ]
        return out


@router.put("/me/assignments", status_code=200)
async def upsert_assignment(body: AssignmentRequest, current_user: dict = Depends(get_current_user)):
    uid = current_user["user_id"]
    async with AsyncSessionLocal() as db:
        # Try update
        res = await db.execute(select(AgentKeyAssignment).where(AgentKeyAssignment.user_id == uid, AgentKeyAssignment.agent_name == body.agent_name))
        a = res.scalar_one_or_none()
        if a is None:
            a = AgentKeyAssignment(
                user_id=uid,
                agent_name=body.agent_name,
                provider=body.provider,
                api_key_id=body.api_key_id,
            )
            db.add(a)
        else:
            a.provider = body.provider
            a.api_key_id = body.api_key_id
        await db.commit()
        return {"id": str(a.id), "agent_name": a.agent_name, "provider": a.provider, "api_key_id": str(a.api_key_id) if a.api_key_id else None}


@router.get("/gemini-status")
async def gemini_key_status(current_user: dict = Depends(get_current_user)):
    """Live status of all Gemini keys — shows daily usage and per-minute rate."""
    return await get_key_status()


@router.get("/keys/gemini-status")
async def gemini_key_status_keys(current_user: dict = Depends(get_current_user)):
    """Alias route used by frontend: /api/keys/gemini-status"""
    return await get_key_status()
