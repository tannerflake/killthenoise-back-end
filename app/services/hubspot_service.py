from __future__ import annotations

import datetime as dt
import os
import time
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.sync_event import SyncEvent
from app.models.tenant_integration import TenantIntegration
from app.services.issue_service import upsert_many

# Base HubSpot API URL (v3 CRM + misc legacy endpoints)
HUBSPOT_BASE_URL = "https://api.hubapi.com"

TICKET_PROPERTIES = [
    "subject",
    "content",
    "hs_lastmodifieddate",
    "hs_pipeline_stage",
    "hs_ticket_priority",
    "hs_createdate",
    "hs_ticket_category",
    "hs_ticket_priority",
    "hs_resolution",
]


class HubSpotService:
    """Multi-tenant async wrapper around HubSpot REST API with change detection."""

    def __init__(self, tenant_id: UUID, integration_id: UUID) -> None:
        self.tenant_id = tenant_id
        self.integration_id = integration_id
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_integration_config(self, session: AsyncSession) -> Dict[str, Any]:
        """Get tenant-specific HubSpot configuration."""
        stmt = select(TenantIntegration).where(
            TenantIntegration.id == self.integration_id,
            TenantIntegration.tenant_id == self.tenant_id,
        )
        result = await session.execute(stmt)
        integration = result.scalar_one_or_none()

        if not integration or not integration.is_active:
            raise ValueError(f"Integration {self.integration_id} not found or inactive")

        return integration.config

    async def _get_client(self, session: AsyncSession) -> httpx.AsyncClient:
        """Get configured HTTP client for this tenant's HubSpot integration."""
        if self._client is None:
            config = await self._get_integration_config(session)
            access_token = config.get("access_token")

            if not access_token:
                raise ValueError("HubSpot access token not configured")

            self._client = httpx.AsyncClient(
                base_url=HUBSPOT_BASE_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=30,
            )

        return self._client

    async def status(self) -> bool:
        """Return True when credentials are valid and HubSpot API responds."""
        async for session in get_db():
            try:
                client = await self._get_client(session)
                r = await client.get("/integrations/v1/me")
                return r.status_code == 200
            except (httpx.HTTPError, ValueError):
                return False
            finally:
                break
        return False

    async def sync_incremental(
        self, since: Optional[dt.datetime] = None
    ) -> Dict[str, Any]:
        """Sync only changes since last sync or specified time."""
        async for session in get_db():
            return await self._sync_with_tracking(session, "incremental", since)

    async def sync_full(self) -> Dict[str, Any]:
        """Perform full sync of all tickets."""
        async for session in get_db():
            return await self._sync_with_tracking(session, "full")

    async def _sync_with_tracking(
        self, session: AsyncSession, sync_type: str, since: Optional[dt.datetime] = None
    ) -> Dict[str, Any]:
        """Sync with comprehensive tracking and error handling."""
        sync_event = SyncEvent(
            tenant_id=self.tenant_id,
            integration_id=self.integration_id,
            event_type=sync_type,
            status="running",
            started_at=dt.datetime.utcnow(),
        )
        session.add(sync_event)
        await session.commit()

        start_time = time.time()

        try:
            # Get last sync time if not specified
            if since is None and sync_type == "incremental":
                integration = await session.get(TenantIntegration, self.integration_id)
                since = integration.last_synced_at

            # Fetch tickets
            tickets = await self._fetch_tickets(since)

            # Transform and upsert
            issue_dicts = []
            for ticket in tickets:
                issue_dict = self._transform_ticket_to_issue(ticket)
                issue_dicts.append(issue_dict)

            if issue_dicts:
                await upsert_many(session, issue_dicts)

            # Update sync event
            duration = int(time.time() - start_time)
            sync_event.status = "success"
            sync_event.completed_at = dt.datetime.utcnow()
            sync_event.duration_seconds = duration
            sync_event.items_processed = len(tickets)
            sync_event.items_updated = len(issue_dicts)

            # Update integration last_synced_at
            integration = await session.get(TenantIntegration, self.integration_id)
            integration.last_synced_at = dt.datetime.utcnow()
            integration.last_sync_status = "success"
            integration.sync_error_message = None

            await session.commit()

            return {
                "success": True,
                "processed": len(tickets),
                "updated": len(issue_dicts),
                "duration_seconds": duration,
            }

        except Exception as e:
            # Update sync event with error
            duration = int(time.time() - start_time)
            sync_event.status = "failed"
            sync_event.completed_at = dt.datetime.utcnow()
            sync_event.duration_seconds = duration
            sync_event.error_message = str(e)

            # Update integration error state
            integration = await session.get(TenantIntegration, self.integration_id)
            integration.last_sync_status = "failed"
            integration.sync_error_message = str(e)

            await session.commit()

            raise

    def _transform_ticket_to_issue(self, ticket: Dict[str, Any]) -> Dict[str, Any]:
        """Transform HubSpot ticket to internal issue format."""
        props = ticket.get("properties", {})

        return {
            "id": uuid.uuid5(uuid.NAMESPACE_URL, f"hubspot-{ticket['id']}"),
            "tenant_id": self.tenant_id,
            "hubspot_ticket_id": str(ticket["id"]),
            "title": props.get("subject") or f"Ticket {ticket['id']}",
            "description": props.get("content"),
            "source": "hubspot",
            "severity": self._calculate_severity(props),
            "frequency": self._calculate_frequency(props),
            "status": props.get("hs_pipeline_stage"),
            "type": props.get("hs_ticket_category"),
            "tags": props.get("hs_ticket_priority"),
        }

    def _calculate_severity(self, props: Dict[str, Any]) -> Optional[int]:
        """Calculate issue severity based on HubSpot ticket properties."""
        priority = props.get("hs_ticket_priority", "").lower()

        severity_map = {"urgent": 5, "high": 4, "medium": 3, "low": 2, "": 1}

        return severity_map.get(priority, 1)

    def _calculate_frequency(self, props: Dict[str, Any]) -> Optional[int]:
        """Calculate issue frequency based on ticket properties."""
        # This could be enhanced with more sophisticated logic
        # For now, return None as frequency calculation requires historical data
        return None

    async def _fetch_tickets(
        self, since: Optional[dt.datetime] = None
    ) -> List[Dict[str, Any]]:
        """Fetch tickets from HubSpot with optional time filtering."""
        async for session in get_db():
            client = await self._get_client(session)
            tickets = []

            params = {
                "limit": 100,
                "properties": ",".join(TICKET_PROPERTIES),
            }

            # Add time filter if specified
            if since:
                # HubSpot uses milliseconds timestamp
                since_ms = int(since.timestamp() * 1000)
                # Note: HubSpot v3 API filtering is done via POST request
                # For simplicity, we'll fetch all and filter client-side for now
                pass

            after_cursor: Optional[str] = None
            while True:
                if after_cursor:
                    params["after"] = after_cursor

                resp = await client.get("/crm/v3/objects/tickets", params=params)
                resp.raise_for_status()
                data = resp.json()

                results = data.get("results", [])

                # Filter by time if needed
                if since:
                    filtered_results = []
                    for ticket in results:
                        props = ticket.get("properties", {})
                        last_modified = props.get("hs_lastmodifieddate")
                        if last_modified:
                            # Parse HubSpot timestamp
                            try:
                                ticket_time = dt.datetime.fromtimestamp(
                                    int(last_modified) / 1000
                                )
                                if ticket_time >= since:
                                    filtered_results.append(ticket)
                            except (ValueError, TypeError):
                                # If we can't parse the timestamp, include it
                                filtered_results.append(ticket)
                    results = filtered_results

                tickets.extend(results)

                paging = data.get("paging")
                if paging and paging.get("next"):
                    after_cursor = paging["next"]["after"]
                else:
                    break

            return tickets

    async def process_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming HubSpot webhook for real-time updates."""
        async for session in get_db():
            # Verify webhook signature (implement security)
            # Extract changed ticket IDs
            ticket_ids = self._extract_ticket_ids_from_webhook(webhook_data)

            if not ticket_ids:
                return {"success": True, "processed": 0}

            # Fetch specific tickets that changed
            client = await self._get_client(session)
            tickets = []

            for ticket_id in ticket_ids:
                try:
                    resp = await client.get(f"/crm/v3/objects/tickets/{ticket_id}")
                    if resp.status_code == 200:
                        tickets.append(resp.json())
                except httpx.HTTPError:
                    continue

            # Transform and upsert
            issue_dicts = [self._transform_ticket_to_issue(t) for t in tickets]

            if issue_dicts:
                await upsert_many(session, issue_dicts)

            # Create sync event for webhook
            sync_event = SyncEvent(
                tenant_id=self.tenant_id,
                integration_id=self.integration_id,
                event_type="webhook",
                status="success",
                items_processed=len(tickets),
                items_updated=len(issue_dicts),
                completed_at=dt.datetime.utcnow(),
                source_data=webhook_data,
            )
            session.add(sync_event)
            await session.commit()

            return {
                "success": True,
                "processed": len(tickets),
                "updated": len(issue_dicts),
            }

    def _extract_ticket_ids_from_webhook(
        self, webhook_data: Dict[str, Any]
    ) -> List[str]:
        """Extract ticket IDs from HubSpot webhook payload."""
        ticket_ids = []

        # HubSpot webhook structure varies by event type
        # This is a simplified extraction
        if "subscriptionType" in webhook_data:
            if webhook_data["subscriptionType"] == "contact.propertyChange":
                # Handle contact property changes
                pass
            elif webhook_data["subscriptionType"] == "ticket.propertyChange":
                # Handle ticket property changes
                ticket_id = webhook_data.get("objectId")
                if ticket_id:
                    ticket_ids.append(str(ticket_id))

        return ticket_ids


# Factory function for creating tenant-specific services
def create_hubspot_service(tenant_id: UUID, integration_id: UUID) -> HubSpotService:
    """Create a HubSpot service instance for a specific tenant."""
    return HubSpotService(tenant_id, integration_id)
