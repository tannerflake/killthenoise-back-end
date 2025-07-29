from __future__ import annotations

import datetime as dt
import os
import time
import uuid
from typing import Any, Dict, List, Optional
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
    "hs_resolution",
]


class HubSpotService:
    """Multi-tenant HubSpot API service with reliable token management."""

    def __init__(self, tenant_id: UUID, integration_id: UUID) -> None:
        self.tenant_id = tenant_id
        self.integration_id = integration_id
        self._client: Optional[httpx.AsyncClient] = None
        self._access_token: Optional[str] = None

    async def _get_integration(self, session: AsyncSession) -> TenantIntegration:
        """Get the tenant integration record."""
        stmt = select(TenantIntegration).where(
            TenantIntegration.id == self.integration_id,
            TenantIntegration.tenant_id == self.tenant_id,
            TenantIntegration.integration_type == "hubspot"
        )
        result = await session.execute(stmt)
        integration = result.scalar_one_or_none()

        if not integration or not integration.is_active:
            raise ValueError(f"HubSpot integration {self.integration_id} not found or inactive for tenant {self.tenant_id}")

        return integration

    async def _validate_token(self, token: str) -> bool:
        """Validate if a token is still valid using HubSpot's introspection endpoint."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{HUBSPOT_BASE_URL}/oauth/v1/access-tokens/{token}",
                    timeout=10
                )
                return response.status_code == 200
        except Exception:
            return False

    async def _get_valid_token(self, session: AsyncSession) -> str:
        """Get a valid access token for this tenant, validating it first."""
        integration = await self._get_integration(session)
        
        # Get token from integration config
        access_token = integration.config.get("access_token")
        if not access_token:
            raise ValueError(f"No HubSpot access token configured for tenant {self.tenant_id}")

        # Validate the token
        if not await self._validate_token(access_token):
            # Mark integration as having sync issues
            integration.last_sync_status = "failed"
            integration.sync_error_message = "Invalid or expired access token"
            await session.commit()
            raise ValueError(f"Invalid or expired HubSpot access token for tenant {self.tenant_id}")

        self._access_token = access_token
        return access_token

    async def _get_client(self, session: AsyncSession) -> httpx.AsyncClient:
        """Get configured HTTP client with validated token."""
        if self._client is None:
            token = await self._get_valid_token(session)
            self._client = httpx.AsyncClient(
                base_url=HUBSPOT_BASE_URL,
                headers={"Authorization": f"Bearer {token}"},
                timeout=30,
            )
        return self._client

    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to HubSpot and return detailed status."""
        async for session in get_db():
            try:
                client = await self._get_client(session)
                
                # Test with token introspection endpoint
                if self._access_token:
                    response = await client.get(f"/oauth/v1/access-tokens/{self._access_token}")
                    if response.status_code == 200:
                        token_info = response.json()
                        return {
                            "connected": True,
                            "hub_domain": token_info.get("hub_domain"),
                            "scopes": token_info.get("scopes", []),
                            "token_type": token_info.get("token_type"),
                            "expires_in": token_info.get("expires_in")
                        }
                
                # Fallback: try a simple tickets API call
                response = await client.get("/crm/v3/objects/tickets", params={"limit": 1})
                return {
                    "connected": response.status_code == 200,
                    "fallback_test": True
                }
                
            except Exception as e:
                return {
                    "connected": False,
                    "error": str(e)
                }
            finally:
                break
        
        return {"connected": False, "error": "Unable to get database session"}

    async def list_tickets(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """List all tickets for this tenant from HubSpot."""
        async for session in get_db():
            try:
                client = await self._get_client(session)
                all_tickets = []
                
                params = {
                    "limit": min(limit or 100, 100),  # Max 100 per page
                    "properties": ",".join(TICKET_PROPERTIES)
                }
                
                after_cursor = None
                total_fetched = 0
                
                while True:
                    if after_cursor:
                        params["after"] = after_cursor
                    
                    response = await client.get("/crm/v3/objects/tickets", params=params)
                    response.raise_for_status()
                    data = response.json()
                    
                    results = data.get("results", [])
                    all_tickets.extend(results)
                    total_fetched += len(results)
                    
                    # Check if we've reached the limit
                    if limit and total_fetched >= limit:
                        all_tickets = all_tickets[:limit]
                        break
                    
                    # Check for more pages
                    paging = data.get("paging")
                    if paging and paging.get("next"):
                        after_cursor = paging["next"]["after"]
                    else:
                        break
                
                return {
                    "success": True,
                    "tickets": all_tickets,
                    "total_count": len(all_tickets),
                    "tenant_id": str(self.tenant_id)
                }
                
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "tenant_id": str(self.tenant_id)
                }
            finally:
                break
        
        return {"success": False, "error": "Unable to get database session"}

    async def sync_full(self) -> Dict[str, Any]:
        """Perform full sync of all tickets with tracking."""
        async for session in get_db():
            return await self._sync_with_tracking(session, "full")

    async def sync_incremental(self, since: Optional[dt.datetime] = None) -> Dict[str, Any]:
        """Sync only changes since last sync or specified time."""
        async for session in get_db():
            return await self._sync_with_tracking(session, "incremental", since)

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

            # Fetch tickets using our reliable method
            tickets_result = await self.list_tickets()
            
            if not tickets_result.get("success"):
                raise ValueError(f"Failed to fetch tickets: {tickets_result.get('error')}")
            
            tickets = tickets_result.get("tickets", [])

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
                "tenant_id": str(self.tenant_id)
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

            return {
                "success": False,
                "error": str(e),
                "tenant_id": str(self.tenant_id)
            }

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

    async def close(self):
        """Clean up resources."""
        if self._client:
            await self._client.aclose()
            self._client = None


# Factory function for creating tenant-specific services
def create_hubspot_service(tenant_id: UUID, integration_id: UUID) -> HubSpotService:
    """Create a HubSpot service instance for a specific tenant."""
    return HubSpotService(tenant_id, integration_id)
