from __future__ import annotations

import asyncio
import datetime as dt
from typing import Any, Dict, List, Optional
from uuid import UUID

import httpx
from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant_integration import TenantIntegration
from app.services.ai_clustering_service import AIIssueClusteringService


class SlackService:
    """Lightweight Slack Web API client and ingestion helpers.

    Stores configuration in `tenant_integrations.config`:
      - token: Slack bot token (xoxb-...)
      - team: Optional workspace/team hint (string)
      - channels: List[str] of selected channel IDs to ingest
    """

    def __init__(self, tenant_id: UUID, session: AsyncSession) -> None:
        self.tenant_id = tenant_id
        self.session = session
        self._integration: Optional[TenantIntegration] = None

    async def _get_integration(self, integration_id: Optional[UUID] = None) -> TenantIntegration:
        if self._integration is not None:
            return self._integration

        stmt = select(TenantIntegration).where(
            and_(
                TenantIntegration.tenant_id == self.tenant_id,
                TenantIntegration.integration_type == "slack",
            )
        )
        if integration_id:
            stmt = stmt.where(TenantIntegration.id == integration_id)

        result = await self.session.execute(stmt)
        integration = result.scalars().first()
        if integration is None:
            raise ValueError("Slack integration not found for tenant")
        self._integration = integration
        return integration

    @staticmethod
    def _auth_headers(token: str) -> Dict[str, str]:
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    async def create_integration(self, *, token: str, team: Optional[str]) -> Dict[str, Any]:
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

    async def list_channels(self, integration_id: UUID | None = None) -> Dict[str, Any]:
        integration = await self._get_integration(integration_id)
        token = (integration.config or {}).get("token")
        if not token:
            return {"success": False, "error": "Slack token missing in integration config"}

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
        integration = await self._get_integration(integration_id)
        token = (integration.config or {}).get("token")
        channel_ids: List[str] = (integration.config or {}).get("channels", [])
        if not token:
            return {"success": False, "error": "Slack token missing in integration config"}
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

