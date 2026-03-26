"""Create a demo user in the local backend database.

Run this from the repository root with the backend venv active:

  /path/to/backend/.venv/bin/python scripts/create_demo_user.py

The script initialises DB tables (idempotent) and inserts a demo user.
"""
import asyncio
import sys

# Ensure backend modules are importable when running from repo root
sys.path.insert(0, "backend")

from database import init_db, AsyncSessionLocal
from database import User


async def create_demo_user():
    await init_db()
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select

        # Check for existing demo user
        result = await session.execute(select(User).where(User.email == "demo@example.com"))
        existing = result.scalars().first()
        if existing:
            print("Demo user already exists:", existing.email)
            return

        user = User(email="demo@example.com", name="Demo User")
        session.add(user)
        await session.commit()
        await session.refresh(user)
        print("Created demo user:", user.email, str(user.id))


if __name__ == "__main__":
    asyncio.run(create_demo_user())
