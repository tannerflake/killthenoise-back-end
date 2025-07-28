from __future__ import annotations

from typing import Dict

from fastapi import APIRouter, BackgroundTasks

from app.services.hubspot_service import hubspot_service


router = APIRouter(prefix="/api/hubspot", tags=["HubSpot"])


@router.get("/status", response_model=Dict[str, bool])
async def hubspot_status() -> Dict[str, bool]:
    """Return connection status to HubSpot via actual API call."""
    connected = await hubspot_service.status()
    return {"connected": connected}


@router.post("/sync")
async def hubspot_sync(background_tasks: BackgroundTasks) -> Dict[str, bool]:
    """Kick off HubSpot tickets sync in the background."""
    background_tasks.add_task(hubspot_service.sync)
    return {"success": True} 