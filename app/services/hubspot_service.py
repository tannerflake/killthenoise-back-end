from __future__ import annotations

import datetime as dt
import logging
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
from app.services.ai_clustering_service import AIIssueClusteringService

# Base HubSpot API URL (v3 CRM + misc legacy endpoints)
HUBSPOT_BASE_URL = "https://api.hubapi.com"

logger = logging.getLogger(__name__)

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

    async def _get_integration(self, session: AsyncSession, require_active: bool = False) -> TenantIntegration:
        """Get the tenant integration record."""
        stmt = select(TenantIntegration).where(
            TenantIntegration.id == self.integration_id,
            TenantIntegration.tenant_id == self.tenant_id,
            TenantIntegration.integration_type == "hubspot"
        )
        result = await session.execute(stmt)
        integration = result.scalar_one_or_none()

        if not integration:
            raise ValueError(f"HubSpot integration {self.integration_id} not found for tenant {self.tenant_id}")
        
        if require_active and not integration.is_active:
            raise ValueError(f"HubSpot integration {self.integration_id} is inactive for tenant {self.tenant_id}")

        return integration

    async def _get_active_integration(self, session: AsyncSession) -> TenantIntegration:
        """Get the active tenant integration record for operations that require tokens."""
        return await self._get_integration(session, require_active=True)

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
        """Get a valid access token for this tenant, refreshing if needed."""
        integration = await self._get_active_integration(session)
        
        # Get tokens from integration config
        access_token = integration.config.get("access_token")
        refresh_token = integration.config.get("refresh_token")
        
        if not access_token:
            raise ValueError(f"No HubSpot access token configured for tenant {self.tenant_id}")

        # Check if token is expired or about to expire (within 5 minutes)
        token_created_at = integration.config.get("token_created_at")
        expires_in = integration.config.get("expires_in", 3600)
        
        if token_created_at and expires_in:
            try:
                created_at = dt.datetime.fromisoformat(token_created_at.replace('Z', '+00:00'))
                expires_at = created_at + dt.timedelta(seconds=expires_in)
                buffer_time = dt.timedelta(minutes=5)
                
                # If token is expired or will expire soon, try to refresh it
                if dt.datetime.utcnow() + buffer_time >= expires_at:
                    if refresh_token:
                        logger.info(f"Token expired for tenant {self.tenant_id}, attempting refresh")
                        new_token = await self._refresh_access_token(session, integration, refresh_token)
                        if new_token:
                            self._access_token = new_token
                            return new_token
                    else:
                        logger.warning(f"No refresh token available for tenant {self.tenant_id}")
            except Exception as e:
                logger.error(f"Error checking token expiration for tenant {self.tenant_id}: {e}")

        # Validate the current token
        if not await self._validate_token(access_token):
            # Try to refresh if we have a refresh token
            if refresh_token:
                logger.info(f"Token validation failed for tenant {self.tenant_id}, attempting refresh")
                new_token = await self._refresh_access_token(session, integration, refresh_token)
                if new_token:
                    self._access_token = new_token
                    return new_token
            
            # Mark integration as having sync issues
            integration.last_sync_status = "failed"
            integration.sync_error_message = "Invalid or expired access token"
            await session.commit()
            raise ValueError(f"Invalid or expired HubSpot access token for tenant {self.tenant_id}")

        self._access_token = access_token
        return access_token

    async def _refresh_access_token(self, session: AsyncSession, integration: TenantIntegration, refresh_token: str) -> Optional[str]:
        """Refresh the access token using the refresh token."""
        try:
            client_id = os.getenv("HUBSPOT_CLIENT_ID")
            client_secret = os.getenv("HUBSPOT_CLIENT_SECRET")
            
            if not client_id or not client_secret:
                logger.error("HubSpot OAuth credentials not configured for token refresh")
                return None
            
            token_data = {
                "grant_type": "refresh_token",
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.hubapi.com/oauth/v1/token",
                    data=token_data,
                    timeout=15
                )
                response.raise_for_status()
                token_response = response.json()
            
            new_access_token = token_response.get("access_token")
            new_refresh_token = token_response.get("refresh_token", refresh_token)  # Use new refresh token if provided
            new_expires_in = token_response.get("expires_in", 3600)
            
            if not new_access_token:
                logger.error(f"Failed to obtain new access token for tenant {self.tenant_id}")
                return None
            
            # Update the integration with new tokens
            integration.config.update({
                "access_token": new_access_token,
                "refresh_token": new_refresh_token,
                "expires_in": new_expires_in,
                "token_created_at": dt.datetime.utcnow().isoformat()
            })
            
            await session.commit()
            logger.info(f"Successfully refreshed access token for tenant {self.tenant_id}")
            return new_access_token
            
        except Exception as e:
            logger.error(f"Failed to refresh access token for tenant {self.tenant_id}: {e}")
            return None

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

    async def test_connection(self, session: AsyncSession) -> Dict[str, Any]:
        """Test connection to HubSpot and return detailed status."""
        try:
            # First, get the integration (can be inactive)
            integration = await self._get_integration(session, require_active=False)
            
            # If integration is inactive, return status without trying to connect
            if not integration.is_active:
                return {
                    "connected": False,
                    "integration_status": "inactive",
                    "message": "Integration exists but is not active. Complete OAuth flow to activate.",
                    "integration_id": str(integration.id),
                    "tenant_id": str(self.tenant_id)
                }
            
            # If no access token configured, return appropriate status
            if not integration.config.get("access_token"):
                return {
                    "connected": False,
                    "integration_status": "active_no_token",
                    "message": "Integration is active but no access token configured.",
                    "integration_id": str(integration.id),
                    "tenant_id": str(self.tenant_id)
                }
            
            # Try to get client and test connection
            client = await self._get_client(session)
            
            # Test with token introspection endpoint
            if self._access_token:
                response = await client.get(f"/oauth/v1/access-tokens/{self._access_token}")
                if response.status_code == 200:
                    token_info = response.json()
                    return {
                        "connected": True,
                        "integration_status": "active_connected",
                        "hub_domain": token_info.get("hub_domain"),
                        "scopes": token_info.get("scopes", []),
                        "token_type": token_info.get("token_type"),
                        "expires_in": token_info.get("expires_in"),
                        "integration_id": str(integration.id),
                        "tenant_id": str(self.tenant_id)
                    }
            
            # Fallback: try a simple tickets API call
            response = await client.get("/crm/v3/objects/tickets", params={"limit": 1})
            return {
                "connected": response.status_code == 200,
                "integration_status": "active_connected",
                "fallback_test": True,
                "integration_id": str(integration.id),
                "tenant_id": str(self.tenant_id)
            }
            
        except Exception as e:
            return {
                "connected": False,
                "error": str(e),
                "integration_id": str(self.integration_id),
                "tenant_id": str(self.tenant_id)
            }

    async def list_tickets(self, session: AsyncSession, limit: Optional[int] = None) -> Dict[str, Any]:
        """List all tickets for this tenant from HubSpot."""
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
            logger.info(f"Starting HubSpot sync for tenant {self.tenant_id}, integration {self.integration_id}")
            
            # Get last sync time if not specified
            if since is None and sync_type == "incremental":
                integration = await session.get(TenantIntegration, self.integration_id)
                since = integration.last_synced_at

            # Fetch tickets using our reliable method
            logger.info("Fetching HubSpot tickets...")
            tickets_result = await self.list_tickets(session)
            logger.info(f"Tickets result: {tickets_result}")
            
            if not tickets_result.get("success"):
                raise ValueError(f"Failed to fetch tickets: {tickets_result.get('error')}")
            
            tickets = tickets_result.get("tickets", [])
            logger.info(f"Fetched {len(tickets)} tickets from HubSpot")

            # Transform and upsert
            logger.info("Transforming tickets to issues...")
            issue_dicts = []
            for ticket in tickets:
                issue_dict = await self._transform_ticket_to_issue(ticket)
                issue_dicts.append(issue_dict)

            if issue_dicts:
                logger.info(f"Upserting {len(issue_dicts)} issues...")
                await upsert_many(session, issue_dicts)

            # Ingest raw reports for AI grouping (v1)
            try:
                logger.info(f"Starting raw report ingestion for {len(tickets)} HubSpot tickets")
                
                # Use the same session for AI clustering to maintain transaction consistency
                clustering = AIIssueClusteringService(self.tenant_id, session)
                
                for ticket in tickets:
                    props = ticket.get("properties", {})
                    title = props.get("subject") or f"Ticket {ticket['id']}"
                    body = props.get("content")
                    
                    logger.debug(f"Processing ticket {ticket['id']}: {title}")
                    
                    await clustering.ingest_raw_report(
                        source="hubspot",
                        external_id=str(ticket["id"]),
                        title=title,
                        body=body,
                        url=None,
                        commit=False,  # Bulk insert without individual commits
                    )
                
                logger.info(f"Successfully ingested {len(tickets)} raw reports from HubSpot")
                
                # Rebuild groups incrementally
                logger.info("Starting reclustering...")
                recluster_result = await clustering.recluster()
                logger.info(f"Reclustering completed: {recluster_result}")
                
            except Exception as e:
                # Log the error but don't fail the sync
                logger.error(f"Error during AI clustering for HubSpot sync: {str(e)}")
                logger.exception("Full traceback:")
                # Continue with sync even if AI clustering fails

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

    async def _transform_ticket_to_issue(self, ticket: Dict[str, Any]) -> Dict[str, Any]:
        """Transform HubSpot ticket to internal issue format with AI enhancement."""
        props = ticket.get("properties", {})

        # Basic ticket data
        base_data = {
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

        # Enhance with AI analysis
        try:
            from app.services.ai_integration_service import create_ai_integration_service
            
            ai_service = create_ai_integration_service(self.tenant_id)
            context = {
                "priority": props.get("hs_ticket_priority"),
                "category": props.get("hs_ticket_category"),
                "source": "hubspot"
            }
            
            enhanced_data = await ai_service.enhance_ticket_data(base_data, context)
            await ai_service.close()
            return enhanced_data
            
        except Exception as e:
            logger.error(f"AI enhancement failed for ticket {ticket['id']}: {e}")
            return base_data

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
