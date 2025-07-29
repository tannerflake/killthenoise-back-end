from __future__ import annotations

from typing import Dict, Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Query, Path
from pydantic import BaseModel

from app.services.scheduler_service import scheduler_service

router = APIRouter(prefix="/api/sync", tags=["Sync"])


class SyncTriggerRequest(BaseModel):
    tenant_id: UUID
    integration_type: str
    sync_type: str = "incremental"  # "incremental" or "full"


@router.get("/status")
async def get_sync_status(
    tenant_id: UUID | None = Query(None, description="Filter by tenant ID")
) -> Dict[str, Any]:
    """Get current sync status for all integrations or a specific tenant."""
    return await scheduler_service.get_sync_status(tenant_id)


@router.post("/trigger")
async def trigger_sync(
    request: SyncTriggerRequest,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """Manually trigger a sync for a specific tenant and integration."""
    background_tasks.add_task(
        scheduler_service.trigger_manual_sync,
        request.tenant_id,
        request.integration_type,
        request.sync_type
    )
    return {
        "success": True,
        "message": f"Sync triggered for tenant {request.tenant_id}, {request.integration_type}"
    }


@router.get("/metrics/{tenant_id}")
async def get_sync_metrics(
    tenant_id: UUID = Path(..., description="Tenant ID"),
    days: int = Query(7, ge=1, le=30, description="Number of days to analyze")
) -> Dict[str, Any]:
    """Get sync performance metrics for a specific tenant."""
    return await scheduler_service.calculate_sync_metrics(tenant_id, days)


@router.post("/start")
async def start_scheduler() -> Dict[str, Any]:
    """Start the background scheduler service."""
    await scheduler_service.start()
    return {"success": True, "message": "Scheduler started"}


@router.post("/stop")
async def stop_scheduler() -> Dict[str, Any]:
    """Stop the background scheduler service."""
    await scheduler_service.stop()
    return {"success": True, "message": "Scheduler stopped"} 