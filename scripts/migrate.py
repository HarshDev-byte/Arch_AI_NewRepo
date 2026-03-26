#!/usr/bin/env python3
"""
migrate.py — Apply ArchAI database schema.

Usage:
  # Auto-migrate via SQLAlchemy (local Postgres / SQLite):
  python scripts/migrate.py

  # Print raw SQL (paste into Supabase SQL editor):
  python scripts/migrate.py --print-sql
"""
import asyncio
import sys
from pathlib import Path

# Ensure backend is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


async def run_sqlalchemy_migration():
    """Use SQLAlchemy to create all tables (idempotent)."""
    from database import init_db
    print("🔄 Running SQLAlchemy init_db()…")
    await init_db()
    print("✅ Schema applied successfully.")


def print_sql():
    """Print the raw SQL migrations to stdout."""
    migrations_dir = Path(__file__).parent.parent / "backend" / "migrations"
    for sql_file in sorted(migrations_dir.glob("*.sql")):
        print(f"\n-- ===== {sql_file.name} =====\n")
        print(sql_file.read_text())


if __name__ == "__main__":
    if "--print-sql" in sys.argv:
        print_sql()
    else:
        asyncio.run(run_sqlalchemy_migration())
