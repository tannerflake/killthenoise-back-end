from __future__ import annotations

import datetime as dt
import os
from typing import Any, List, AsyncGenerator

import httpx
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.services.issue_service import upsert_many

# Base HubSpot API URL (v3 CRM + misc legacy endpoints)
HUBSPOT_BASE_URL = "https://api.hubapi.com"

TICKET_PROPERTIES = [
    "subject",
    "content",
    "hs_lastmodifieddate",
    "hs_pipeline_stage",
    "hs_ticket_priority",
]


class HubSpotService:
    """Minimal async wrapper around HubSpot REST API.

    For now we support a simple connectivity check and ticket sync skeleton.
    Later we will extend this class with OAuth refresh, incremental paging, etc.
    """

    def __init__(self) -> None:
        # Prefer private-app token for dev; later we'll support OAuth access tokens.
        self._access_token: str | None = os.getenv("HUBSPOT_ACCESS_TOKEN")
        if not self._access_token:
            # Fallback to env var pattern used in the task description.
            self._access_token = os.getenv("HUBSPOT_SERVICE_ROLE_KEY")  # type: ignore[assignment]

        self._client = httpx.AsyncClient(
            base_url=HUBSPOT_BASE_URL,
            headers={"Authorization": f"Bearer {self._access_token}"},
            timeout=30,
        )

    # ---------------------------------------------------------------------
    # Public helpers
    # ---------------------------------------------------------------------

    async def status(self) -> bool:
        """Return True when credentials are valid and HubSpot API responds."""
        try:
            r = await self._client.get("/integrations/v1/me")
            return r.status_code == 200
        except httpx.HTTPError:
            return False

    async def sync(self) -> None:
        """Background job placeholder that will fetch & upsert tickets."""
        # TODO: determine last sync timestamp (store in DB / cache)
        # last_synced_at = await self._get_last_synced_at()
        tickets: List[dict[str, Any]] = await self._fetch_tickets()

        issue_dicts: List[dict[str, Any]] = []
        for t in tickets:
            props = t.get("properties", {})
            issue_dicts.append(
                {
                    "hubspot_ticket_id": str(t["id"]),
                    "id": uuid.uuid5(uuid.NAMESPACE_URL, f"hubspot-{t['id']}").hex,
                    "title": props.get("subject") or f"Ticket {t['id']}",
                    "description": props.get("content"),
                    "source": "hubspot",
                    "severity": None,
                    "frequency": None,
                    "status": props.get("hs_pipeline_stage"),
                    "type": None,
                    "tags": props.get("hs_ticket_priority"),
                }
            )

        if not issue_dicts:
            return

        async for session in get_db():  # type: AsyncGenerator
            await upsert_many(session, issue_dicts)
            break

        print(f"[HubSpotService] Synced {len(issue_dicts)} HubSpot tickets → issues.")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _fetch_tickets(self, after: dt.datetime | None = None) -> List[dict[str, Any]]:
        """Fetch tickets from HubSpot CRM v3 objects API with basic pagination."""
        tickets: list[dict[str, Any]] = []

        params = {
            "limit": 100,
            "properties": ",".join(TICKET_PROPERTIES),
        }
        if after:
            # HubSpot uses filter groups in POST request for updated_after; skip for now.
            pass

        after_cursor: str | None = None
        while True:
            if after_cursor:
                params["after"] = after_cursor

            resp = await self._client.get("/crm/v3/objects/tickets", params=params)
            resp.raise_for_status()
            data = resp.json()

            tickets.extend(data.get("results", []))

            paging = data.get("paging")
            if paging and paging.get("next"):
                after_cursor = paging["next"]["after"]
            else:
                break

        return tickets


# Singleton instance used by routers
hubspot_service = HubSpotService() 