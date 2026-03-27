#!/usr/bin/env python3
"""
Initialize the database with proper tables
"""
import asyncio
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from database import async_engine, Base

async def init_database():
    """Initialize database tables"""
    print("🔧 Initializing database...")
    
    async with async_engine.begin() as conn:
        # Drop all tables first
        await conn.run_sync(Base.metadata.drop_all)
        print("   - Dropped existing tables")
        
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
        print("   - Created all tables")
    
    print("✅ Database initialized successfully!")

if __name__ == "__main__":
    asyncio.run(init_database())