from __future__ import annotations

import os
import asyncio

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import Base, engine

# Load environment variables early
load_dotenv()

from app.api import (analytics, hubspot, health, integrations, issues,  # noqa: E402
                     jira, sync, webhooks, slack, settings, teams)
from app.services.scheduler_service import scheduler_service  # noqa: E402
from app.services.background_sync_service import background_sync_service  # noqa: E402

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
async def startup_event():
    """Startup event handler."""
    print("[Startup] Using Alembic for database migrations")
    print("[Startup] Scheduler service started")
    print("[Startup] Background sync service started")
    
    # Start scheduler service
    await scheduler_service.start()
    
    # Start background sync service
    asyncio.create_task(background_sync_service.start())


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler."""
    print("[Shutdown] Scheduler service stopped")
    print("[Shutdown] Background sync service stopped")
    
    # Stop scheduler service
    await scheduler_service.stop()
    
    # Stop background sync service
    await background_sync_service.stop()

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
app.include_router(settings.router)
app.include_router(teams.router)


@app.get("/health")
async def health_check():
    """Basic health check endpoint for Railway."""
    return {"status": "healthy", "message": "Service is running"}
