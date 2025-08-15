from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import Base, engine

# Load environment variables early
load_dotenv()

from app.api import (analytics, hubspot, health, integrations, issues,  # noqa: E402
                     jira, sync, webhooks, slack)
from app.services.scheduler_service import scheduler_service  # noqa: E402

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
    """Start scheduler and verify database connection."""
    
    # NOTE: Database tables are now managed by Alembic migrations
    # Run 'alembic upgrade head' to create/update tables
    print("[Startup] Using Alembic for database migrations")

    # Start the scheduler service
    try:
        await scheduler_service.start()
        print("[Startup] Scheduler service started")
    except Exception as exc:
        print(f"[Startup] Failed to start scheduler: {exc!r}")


@app.on_event("shutdown")
async def on_shutdown() -> None:
    """Stop scheduler and dispose database connections."""
    try:
        await scheduler_service.stop()
        print("[Shutdown] Scheduler service stopped")
    except Exception as exc:
        print(f"[Shutdown] Error stopping scheduler: {exc!r}")

    await engine.dispose()


# Include API routers
app.include_router(health.router)
app.include_router(hubspot.router)
app.include_router(issues.router)
app.include_router(integrations.router)
app.include_router(jira.router)
app.include_router(sync.router)
app.include_router(analytics.router)
app.include_router(webhooks.router)
app.include_router(slack.router)
