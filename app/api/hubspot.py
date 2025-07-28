from __future__ import annotations

from typing import Dict

from fastapi import APIRouter, BackgroundTasks

router = APIRouter(prefix="/api/hubspot", tags=["HubSpot"])


@router.get("/status", response_model=Dict[str, bool])
async def hubspot_status() -> Dict[str, bool]:
    """Return connection status to HubSpot (stubbed for now)."""
    return {"connected": False}


async def _sync_hubspot_job() -> None:
    """Placeholder for sync job."""
    # TODO: implement actual sync
    return None


@router.post("/sync")
async def hubspot_sync(background_tasks: BackgroundTasks) -> Dict[str, bool]:
    """Kick off HubSpot tickets sync in the background."""
    background_tasks.add_task(_sync_hubspot_job)
    return {"success": True} 