from __future__ import annotations

import asyncio
import datetime as dt
import logging
import os
from typing import Any, Dict, List, Optional
from uuid import UUID

import httpx
from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant_integration import TenantIntegration
from app.services.ai_clustering_service import AIIssueClusteringService

logger = logging.getLogger(__name__)


class SlackService:
    """Enhanced Slack Web API client with OAuth support and token refresh.

    Stores configuration in `tenant_integrations.config`:
      - access_token: Slack OAuth access token
      - refresh_token: Slack OAuth refresh token (for persistent auth)
      - expires_in: Token expiration time in seconds
      - token_created_at: ISO timestamp when token was created
      - team: Optional workspace/team hint (string)
      - channels: List[str] of selected channel IDs to ingest
    """

    def __init__(self, tenant_id: UUID, integration_id: Optional[UUID] = None, session: Optional[AsyncSession] = None) -> None:
        self.tenant_id = tenant_id
        self.integration_id = integration_id
        self.session = session
        self._integration: Optional[TenantIntegration] = None
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None

    async def _get_integration(self, integration_id: Optional[UUID] = None) -> TenantIntegration:
        if self._integration is not None:
            return self._integration

        target_integration_id = integration_id or self.integration_id
        
        stmt = select(TenantIntegration).where(
            and_(
                TenantIntegration.tenant_id == self.tenant_id,
                TenantIntegration.integration_type == "slack",
            )
        )
        if target_integration_id:
            stmt = stmt.where(TenantIntegration.id == target_integration_id)

        result = await self.session.execute(stmt)
        integration = result.scalars().first()
        if integration is None:
            raise ValueError("Slack integration not found for tenant")
        self._integration = integration
        return integration

    async def _get_valid_token(self, session: AsyncSession) -> str:
        """Get a valid access token, refreshing if necessary."""
        integration = await self._get_integration()
        config = integration.config or {}
        
        access_token = config.get("access_token")
        refresh_token = config.get("refresh_token")
        expires_in = config.get("expires_in", 3600)
        token_created_at = config.get("token_created_at")
        
        if not access_token:
            raise ValueError("No access token found in integration config")
        
        # Check if token is expired (with 5-minute buffer)
        if token_created_at and expires_in and expires_in > 0:
            try:
                created_at = dt.datetime.fromisoformat(token_created_at)
                expires_at = created_at + dt.timedelta(seconds=expires_in)
                buffer_time = dt.timedelta(minutes=5)
                
                if dt.datetime.utcnow() + buffer_time >= expires_at:
                    if refresh_token:
                        logger.info(f"Refreshing expired Slack token for tenant {self.tenant_id}")
                        new_token = await self._refresh_access_token(session, integration, refresh_token)
                        if new_token:
                            return new_token
                        else:
                            raise ValueError("Failed to refresh access token")
                    else:
                        # For Slack OAuth v2, tokens can be long-lived and may not need refresh
                        # Let's test the token first before assuming it's expired
                        logger.info(f"Token appears expired but no refresh token available. Testing token validity for tenant {self.tenant_id}")
                        if await self._test_token_validity(access_token):
                            logger.info(f"Token is still valid despite expiration time for tenant {self.tenant_id}")
                            return access_token
                        else:
                            raise ValueError("Token expired and no refresh token available")
            except (ValueError, TypeError) as e:
                logger.warning(f"Error parsing token expiration for tenant {self.tenant_id}: {str(e)}")
                # Continue with the token as-is
        
        return access_token

    async def _test_token_validity(self, token: str) -> bool:
        """Test if a Slack token is still valid by making a simple API call."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://slack.com/api/auth.test",
                    headers=self._auth_headers(token)
                )
                data = response.json()
                return data.get("ok", False)
        except Exception as e:
            logger.error(f"Error testing token validity: {str(e)}")
            return False

    async def _refresh_access_token(self, session: AsyncSession, integration: TenantIntegration, refresh_token: str) -> Optional[str]:
        """Refresh the access token using the refresh token."""
        try:
            client_id = os.getenv("SLACK_CLIENT_ID")
            client_secret = os.getenv("SLACK_CLIENT_SECRET")
            
            if not client_id or not client_secret:
                logger.error("Slack OAuth credentials not configured for token refresh")
                return None
            
            token_data = {
                "grant_type": "refresh_token",
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://slack.com/api/oauth.v2.access",
                    data=token_data,
                    timeout=15
                )
                response.raise_for_status()
                token_response = response.json()
            
            if not token_response.get("ok"):
                logger.error(f"Slack token refresh failed: {token_response.get('error')}")
                return None
            
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
            logger.error(f"Error refreshing Slack token for tenant {self.tenant_id}: {str(e)}")
            return None

    @staticmethod
    def _auth_headers(token: str) -> Dict[str, str]:
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    async def create_integration(self, *, token: str, team: Optional[str]) -> Dict[str, Any]:
        """Create a new Slack integration with bot token (legacy method)."""
        if not token or not token.startswith("xoxb-") or len(token) < 20:
            return {"success": False, "error": "Invalid Slack bot token"}

        payload: Dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "integration_type": "slack",
            "is_active": True,
            "config": {"token": token, "team": team or None, "channels": []},
        }

        integration = TenantIntegration(**payload)
        self.session.add(integration)
        await self.session.commit()
        await self.session.refresh(integration)
        self._integration = integration
        return {"success": True, "integration_id": str(integration.id)}

    async def create_oauth_integration(self, *, access_token: str, refresh_token: str, team: Optional[str] = None, expires_in: int = 3600) -> Dict[str, Any]:
        """Create a new Slack integration with OAuth tokens."""
        if not access_token or not refresh_token:
            return {"success": False, "error": "Invalid OAuth tokens"}

        payload: Dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "integration_type": "slack",
            "is_active": True,
            "config": {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_in": expires_in,
                "token_created_at": dt.datetime.utcnow().isoformat(),
                "team": team,
                "channels": []
            },
        }

        integration = TenantIntegration(**payload)
        self.session.add(integration)
        await self.session.commit()
        await self.session.refresh(integration)
        self._integration = integration
        return {"success": True, "integration_id": str(integration.id)}

    async def list_channels(self, integration_id: UUID | None = None) -> Dict[str, Any]:
        """List available Slack channels using OAuth token."""
        try:
            integration = await self._get_integration(integration_id)
            
            # Try to get a valid token (with refresh if needed)
            token = await self._get_valid_token(self.session)
            
            channels: List[Dict[str, Any]] = []
            cursor: Optional[str] = None
            async with httpx.AsyncClient(timeout=20.0) as client:
                while True:
                    params = {
                        "types": "public_channel,private_channel",
                        "limit": 200,
                    }
                    if cursor:
                        params["cursor"] = cursor
                    resp = await client.get(
                        "https://slack.com/api/conversations.list",
                        headers=self._auth_headers(token),
                        params=params,
                    )
                    data = resp.json()
                    if not data.get("ok"):
                        return {"success": False, "error": data.get("error", "slack_error")}
                    channels.extend(data.get("channels", []))
                    cursor = (data.get("response_metadata") or {}).get("next_cursor")
                    if not cursor:
                        break

            selected = (integration.config or {}).get("channels", [])
            items = [
                {"id": c.get("id"), "name": c.get("name"), "selected": c.get("id") in selected}
                for c in channels
                if c.get("is_channel") or True
            ]
            return {"success": True, "channels": items}
            
        except ValueError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Error listing Slack channels: {str(e)}")
            return {"success": False, "error": "Failed to list channels"}

    async def update_selected_channels(self, *, channel_ids: List[str], integration_id: UUID | None = None) -> Dict[str, Any]:
        integration = await self._get_integration(integration_id)
        config = dict(integration.config or {})
        config["channels"] = list({c for c in channel_ids if c})

        await self.session.execute(
            update(TenantIntegration)
            .where(TenantIntegration.id == integration.id)
            .values(config=config)
        )
        await self.session.commit()
        integration.config = config
        return {"success": True, "channels": config["channels"]}

    async def sync_messages(self, *, integration_id: UUID | None = None, lookback_days: int = 7) -> Dict[str, Any]:
        """Sync Slack messages using OAuth token."""
        try:
            integration = await self._get_integration(integration_id)
            token = await self._get_valid_token(self.session)
            channel_ids: List[str] = (integration.config or {}).get("channels", [])
            
            if not channel_ids:
                return {"success": True, "ingested": 0}

            oldest_ts = (dt.datetime.utcnow() - dt.timedelta(days=lookback_days)).timestamp()
            clustering = AIIssueClusteringService(self.tenant_id, self.session)

            async with httpx.AsyncClient(timeout=30.0) as client:
                tasks = [
                    self._sync_channel_messages(client, token, channel_id, oldest_ts, clustering)
                    for channel_id in channel_ids
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)

            total = 0
            for r in results:
                if isinstance(r, Exception):
                    continue
                total += int(r)

            await self.session.commit()
            await clustering.recluster()
            return {"success": True, "ingested": total}
            
        except ValueError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Error syncing Slack messages: {str(e)}")
            return {"success": False, "error": "Failed to sync messages"}

    async def _sync_channel_messages(
        self,
        client: httpx.AsyncClient,
        token: str,
        channel_id: str,
        oldest_ts: float,
        clustering: AIIssueClusteringService,
    ) -> int:
        ingested = 0
        cursor: Optional[str] = None
        while True:
            params = {
                "channel": channel_id,
                "limit": 200,
                "oldest": f"{oldest_ts:.6f}",
                "inclusive": True,
            }
            if cursor:
                params["cursor"] = cursor
            resp = await client.get(
                "https://slack.com/api/conversations.history",
                headers=self._auth_headers(token),
                params=params,
            )
            data = resp.json()
            if not data.get("ok"):
                break

            for msg in data.get("messages", []):
                if msg.get("subtype") in {"channel_join", "channel_leave"}:
                    continue
                ts = msg.get("ts")
                text = (msg.get("text") or "").strip()
                if not ts or not text:
                    continue
                title = text.split("\n", 1)[0][:80] or "Slack message"
                body = text
                external_id = f"{channel_id}:{ts}"
                await clustering.ingest_raw_report(
                    source="slack",
                    external_id=external_id,
                    title=title,
                    body=body,
                    url=None,
                    commit=False,
                )
                ingested += 1

            cursor = (data.get("response_metadata") or {}).get("next_cursor")
            if not cursor:
                break
        return ingested

    async def close(self) -> None:
        """Close the service and clean up resources."""
        if self.session:
            await self.session.close()

