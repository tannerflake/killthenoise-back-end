from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import Base, engine

# Load environment variables early
load_dotenv()

from app.api import hubspot, integrations, issues, jira  # noqa: E402

app = FastAPI(title="KillTheNoise API")

# CORS setup
origins = [os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Startup / shutdown hooks
# ---------------------------------------------------------------------------


@app.on_event("startup")
async def on_startup() -> None:
    """Create database tables if they don't exist (simple auto-migration)."""

    async def _create() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    try:
        await _create()
    except Exception as exc:  # pragma: no cover
        # Log but don't crash the app; handle outside if needed
        print(f"[Startup] Failed to create tables: {exc!r}")


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await engine.dispose()

# Include API routers
app.include_router(hubspot.router)
app.include_router(issues.router)
app.include_router(integrations.router)
app.include_router(jira.router) 