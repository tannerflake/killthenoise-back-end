from __future__ import annotations

import asyncio
import datetime as dt
import logging
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.tenant_integration import TenantIntegration
from app.services.calculation_service import create_calculation_service
from app.services.hubspot_service import create_hubspot_service

logger = logging.getLogger(__name__)


class SchedulerService:
    """Service for managing periodic sync operations across multiple tenants."""

    def __init__(self):
        self.running = False
        self.sync_tasks: Dict[UUID, asyncio.Task] = {}
        self.sync_intervals = {
            "hubspot": 300,  # 5 minutes
            "jira": 600,  # 10 minutes
            "default": 900,  # 15 minutes
        }

    async def start(self) -> None:
        """Start the scheduler service."""
        if self.running:
            return

        self.running = True
        logger.info("Starting scheduler service")

        # Start background task
        asyncio.create_task(self._run_scheduler())

    async def stop(self) -> None:
        """Stop the scheduler service."""
        self.running = False

        # Cancel all running sync tasks
        for task in self.sync_tasks.values():
            if not task.done():
                task.cancel()

        logger.info("Stopped scheduler service")

    async def _run_scheduler(self) -> None:
        """Main scheduler loop."""
        while self.running:
            try:
                await self._sync_all_tenants()
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(60)

    async def _sync_all_tenants(self) -> None:
        """Sync all active tenant integrations."""
        async for session in get_db():
            # Get all active integrations
            stmt = select(TenantIntegration).where(
                and_(
                    TenantIntegration.is_active == True,
                    TenantIntegration.last_synced_at.isnot(None),
                )
            )
            result = await session.execute(stmt)
            integrations = result.scalars().all()

            for integration in integrations:
                await self._check_and_sync_integration(integration)

            break

    async def _check_and_sync_integration(self, integration: TenantIntegration) -> None:
        """Check if integration needs syncing and start sync if needed."""
        now = dt.datetime.utcnow()

        # Calculate time since last sync
        if integration.last_synced_at:
            time_since_sync = (now - integration.last_synced_at).total_seconds()
        else:
            time_since_sync = float("inf")

        # Get sync interval for this integration type
        sync_interval = self.sync_intervals.get(
            integration.integration_type, self.sync_intervals["default"]
        )

        # Check if it's time to sync
        if time_since_sync >= sync_interval:
            # Check if there's already a sync task running for this integration
            if integration.id in self.sync_tasks:
                task = self.sync_tasks[integration.id]
                if not task.done():
                    logger.debug(
                        f"Sync already running for integration {integration.id}"
                    )
                    return
                else:
                    # Clean up completed task
                    del self.sync_tasks[integration.id]

            # Start new sync task
            logger.info(
                f"Starting sync for integration {integration.id} ({integration.integration_type})"
            )
            task = asyncio.create_task(
                self._sync_integration(integration), name=f"sync_{integration.id}"
            )
            self.sync_tasks[integration.id] = task

    async def _sync_integration(self, integration: TenantIntegration) -> None:
        """Perform sync for a specific integration."""
        try:
            if integration.integration_type == "hubspot":
                service = create_hubspot_service(integration.tenant_id, integration.id)
                result = await service.sync_incremental()
                logger.info(
                    f"HubSpot sync completed for tenant {integration.tenant_id}: {result}"
                )

            elif integration.integration_type == "jira":
                # TODO: Implement Jira sync
                logger.info(
                    f"Jira sync not yet implemented for integration {integration.id}"
                )

            else:
                logger.warning(
                    f"Unknown integration type: {integration.integration_type}"
                )

        except Exception as e:
            logger.error(f"Sync failed for integration {integration.id}: {e}")

            # Update integration error state
            async for session in get_db():
                integration = await session.get(TenantIntegration, integration.id)
                if integration:
                    integration.last_sync_status = "failed"
                    integration.sync_error_message = str(e)
                    await session.commit()
                break

    async def trigger_manual_sync(
        self, tenant_id: UUID, integration_type: str, sync_type: str = "incremental"
    ) -> Dict[str, Any]:
        """Manually trigger a sync for a specific tenant and integration type."""
        async for session in get_db():
            # Find the integration
            stmt = select(TenantIntegration).where(
                and_(
                    TenantIntegration.tenant_id == tenant_id,
                    TenantIntegration.integration_type == integration_type,
                    TenantIntegration.is_active == True,
                )
            )
            result = await session.execute(stmt)
            integration = result.scalar_one_or_none()

            if not integration:
                return {
                    "success": False,
                    "error": f"No active {integration_type} integration found for tenant {tenant_id}",
                }

            # Start manual sync
            try:
                if integration_type == "hubspot":
                    service = create_hubspot_service(tenant_id, integration.id)
                    if sync_type == "full":
                        result = await service.sync_full()
                    else:
                        result = await service.sync_incremental()

                    return {
                        "success": True,
                        "integration_id": str(integration.id),
                        "sync_type": sync_type,
                        "result": result,
                    }

                else:
                    return {
                        "success": False,
                        "error": f"Manual sync not implemented for {integration_type}",
                    }

            except Exception as e:
                return {"success": False, "error": str(e)}

    async def get_sync_status(self, tenant_id: Optional[UUID] = None) -> Dict[str, Any]:
        """Get current sync status for all integrations or a specific tenant."""
        async for session in get_db():
            stmt = select(TenantIntegration)
            if tenant_id:
                stmt = stmt.where(TenantIntegration.tenant_id == tenant_id)

            result = await session.execute(stmt)
            integrations = result.scalars().all()

            status = {"running_tasks": len(self.sync_tasks), "integrations": []}

            for integration in integrations:
                task = self.sync_tasks.get(integration.id)
                task_status = "running" if task and not task.done() else "idle"

                status["integrations"].append(
                    {
                        "id": str(integration.id),
                        "tenant_id": str(integration.tenant_id),
                        "type": integration.integration_type,
                        "active": integration.is_active,
                        "last_synced_at": (
                            integration.last_synced_at.isoformat()
                            if integration.last_synced_at
                            else None
                        ),
                        "last_sync_status": integration.last_sync_status,
                        "task_status": task_status,
                        "error_message": integration.sync_error_message,
                    }
                )

            return status

    async def calculate_sync_metrics(
        self, tenant_id: UUID, days: int = 7
    ) -> Dict[str, Any]:
        """Calculate sync performance metrics for a tenant."""
        calc_service = create_calculation_service(tenant_id)
        return await calc_service.calculate_sync_health(days)


# Global scheduler instance
scheduler_service = SchedulerService()
