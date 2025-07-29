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
        """Create bare client; token headers are injected dynamically."""

        self._client = httpx.AsyncClient(base_url=HUBSPOT_BASE_URL, timeout=30)

        # OAuth app credentials (static)
        self._client_id: str | None = os.getenv("HUBSPOT_CLIENT_ID")
        self._client_secret: str | None = os.getenv("HUBSPOT_CLIENT_SECRET")

        if not self._client_id or not self._client_secret:
            raise RuntimeError("HUBSPOT_CLIENT_ID and HUBSPOT_CLIENT_SECRET must be set.")

    # ------------------------------------------------------------------
    # Internal helpers for token management
    # ------------------------------------------------------------------

    async def _inject_auth_header(self) -> None:
        """Ensure we have a valid access token and set it on the httpx client."""
        from app.services import token_service  # local import to avoid cycles

        async for session in get_db():
            access_token = await token_service.get_valid_access_token(
                session=session,
                provider="hubspot",
                client_id=self._client_id,
                client_secret=self._client_secret,
            )
            break

        if not access_token:
            raise RuntimeError(
                "No HubSpot access token available. Complete OAuth flow first."
            )

        self._client.headers["Authorization"] = f"Bearer {access_token}"

    # ---------------------------------------------------------------------
    # Public helpers
    # ---------------------------------------------------------------------

    async def status(self) -> bool:
        """Return True when credentials are valid and HubSpot API responds."""
        await self._inject_auth_header()
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
        await self._inject_auth_header()
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

    # ------------------------------------------------------------------
    # OAuth helpers (called from API router)
    # ------------------------------------------------------------------

    async def exchange_code_for_tokens(self, code: str) -> None:
        """Exchange an OAuth authorization code for tokens and persist them."""
        if not self._client_id or not self._client_secret:
            raise RuntimeError("HubSpot OAuth client credentials missing.")

        data = {
            "grant_type": "authorization_code",
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "redirect_uri": os.getenv("HUBSPOT_REDIRECT_URI"),
            "code": code,
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.hubapi.com/oauth/v1/token",
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            resp.raise_for_status()

        payload = resp.json()

        from app.services import token_service  # local import

        async for session in get_db():  # type: AsyncGenerator
            await token_service.save_or_update(
                session=session,
                provider="hubspot",
                access_token=payload["access_token"],
                refresh_token=payload["refresh_token"],
                expires_in=payload["expires_in"],
            )
            break


# Singleton instance used by routers
hubspot_service = HubSpotService() 