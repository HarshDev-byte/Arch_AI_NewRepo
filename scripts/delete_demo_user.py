"""Delete the demo user (demo@example.com) from the local backend DB.

Run from repo root with backend venv python:

  /path/to/backend/.venv/bin/python scripts/delete_demo_user.py
"""
import asyncio
import sys

sys.path.insert(0, "backend")

from database import init_db, AsyncSessionLocal
from database import User
from sqlalchemy import select


async def delete_demo_user():
    await init_db()
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == "demo@example.com"))
        user = result.scalars().first()
        if not user:
            print("No demo user found (demo@example.com).")
            return
        await session.delete(user)
        await session.commit()
        print("Deleted demo user:", user.email, str(user.id))


if __name__ == "__main__":
    asyncio.run(delete_demo_user())
