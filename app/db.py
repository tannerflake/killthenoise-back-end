from __future__ import annotations

import os

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Load env before anything else
load_dotenv()

# Environment variables
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

# SQLAlchemy engine & session
engine = create_async_engine(DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

# Declarative base for models
Base = declarative_base()


async def get_db():
    """FastAPI dependency that yields an async database session."""
    async with AsyncSessionLocal() as session:
        yield session


# Supabase client (optional)
from typing import Optional

from supabase import Client, create_client

SUPABASE: Optional[Client] = None
if SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY:
    SUPABASE = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
