from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.tenant_integration import TenantIntegration
from app.services.hubspot_service import HubSpotService
from app.services.jira_service import JiraService
from app.services.ai_clustering_service import AIIssueClusteringService

logger = logging.getLogger(__name__)


class BackgroundSyncService:
    """Service for background syncing of integrations and AI clustering."""
    
    def __init__(self):
        self.running = False
        self.sync_interval = 300  # 5 minutes
        self.last_sync_times: Dict[str, datetime] = {}
    
    async def start(self):
        """Start the background sync service."""
        if self.running:
            logger.warning("Background sync service is already running")
            return
        
        self.running = True
        logger.info("Starting background sync service")
        
        while self.running:
            try:
                await self._run_sync_cycle()
                await asyncio.sleep(self.sync_interval)
            except Exception as e:
                logger.error(f"Error in background sync cycle: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    async def stop(self):
        """Stop the background sync service."""
        self.running = False
        logger.info("Stopping background sync service")
    
    async def _run_sync_cycle(self):
        """Run one complete sync cycle for all active integrations."""
        logger.info("Starting background sync cycle")
        
        async for session in get_db():
            try:
                # Get all active integrations
                stmt = select(TenantIntegration).where(TenantIntegration.is_active == True)
                result = await session.execute(stmt)
                integrations = result.scalars().all()
                
                for integration in integrations:
                    await self._sync_integration(integration, session)
                
                logger.info(f"Completed background sync cycle for {len(integrations)} integrations")
                
            except Exception as e:
                logger.error(f"Error in sync cycle: {e}")
            finally:
                await session.close()
    
    async def _sync_integration(self, integration: TenantIntegration, session: AsyncSession):
        """Sync a single integration and process through AI clustering."""
        integration_key = f"{integration.tenant_id}_{integration.integration_type}"
        
        try:
            # Check if we should sync this integration (avoid too frequent syncs)
            last_sync = self.last_sync_times.get(integration_key)
            if last_sync and datetime.utcnow() - last_sync < timedelta(minutes=5):
                return
            
            logger.info(f"Syncing integration {integration.integration_type} for tenant {integration.tenant_id}")
            
            # Sync based on integration type
            if integration.integration_type == "hubspot":
                await self._sync_hubspot(integration, session)
            elif integration.integration_type == "jira":
                await self._sync_jira(integration, session)
            # Add other integration types as needed
            
            # Update last sync time
            self.last_sync_times[integration_key] = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Error syncing integration {integration.integration_type}: {e}")
    
    async def _sync_hubspot(self, integration: TenantIntegration, session: AsyncSession):
        """Sync HubSpot integration and process through AI clustering."""
        try:
            # Create HubSpot service
            hubspot_service = HubSpotService(integration.tenant_id, session)
            
            # Get recent tickets (last 24 hours)
            since = datetime.utcnow() - timedelta(hours=24)
            tickets_data = await hubspot_service._sync_with_tracking(session, "background", since)
            
            if tickets_data.get("success"):
                tickets = tickets_data.get("tickets", [])
                logger.info(f"Found {len(tickets)} new HubSpot tickets")
                
                # Process through AI clustering
                await self._process_tickets_through_ai(tickets, "hubspot", integration.tenant_id, session)
            
        except Exception as e:
            logger.error(f"Error in HubSpot sync: {e}")
    
    async def _sync_jira(self, integration: TenantIntegration, session: AsyncSession):
        """Sync Jira integration and process through AI clustering."""
        try:
            # Create Jira service
            jira_service = JiraService(integration.tenant_id, session)
            
            # Get recent issues (last 24 hours)
            since = datetime.utcnow() - timedelta(hours=24)
            issues_data = await jira_service._sync_with_tracking(session, "background", since)
            
            if issues_data.get("success"):
                issues = issues_data.get("issues", [])
                logger.info(f"Found {len(issues)} new Jira issues")
                
                # Process through AI clustering
                await self._process_tickets_through_ai(issues, "jira", integration.tenant_id, session)
            
        except Exception as e:
            logger.error(f"Error in Jira sync: {e}")
    
    async def _process_tickets_through_ai(self, tickets: List[Dict], source: str, tenant_id: UUID, session: AsyncSession):
        """Process tickets through AI clustering system."""
        try:
            # Create AI clustering service
            clustering = AIIssueClusteringService(tenant_id, session)
            
            processed_count = 0
            for ticket in tickets:
                try:
                    # Extract ticket data
                    if source == "hubspot":
                        props = ticket.get("properties", {})
                        title = props.get("subject") or f"Ticket {ticket['id']}"
                        body = props.get("content")
                        external_id = str(ticket["id"])
                    elif source == "jira":
                        fields = ticket.get("fields", {})
                        title = fields.get("summary") or ticket.get("key")
                        body = fields.get("description")
                        external_id = ticket.get("key")
                    else:
                        continue
                    
                    # Ingest into AI clustering system
                    await clustering.ingest_raw_report(
                        source=source,
                        external_id=external_id,
                        title=title,
                        body=body,
                        url=None,
                        commit=False  # Bulk insert without individual commits
                    )
                    processed_count += 1
                    
                except Exception as e:
                    logger.error(f"Error processing ticket {ticket.get('id', 'unknown')}: {e}")
                    continue
            
            # Commit all changes
            await session.commit()
            
            # Run AI clustering to group similar issues
            if processed_count > 0:
                logger.info(f"Running AI clustering for {processed_count} new {source} tickets")
                clustering_result = await clustering.recluster()
                logger.info(f"AI clustering completed: {clustering_result}")
            
        except Exception as e:
            logger.error(f"Error in AI processing: {e}")


# Global instance
background_sync_service = BackgroundSyncService()
