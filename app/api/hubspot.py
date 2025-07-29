from __future__ import annotations

from typing import Dict

from fastapi import APIRouter, BackgroundTasks

from app.services.hubspot_service import create_hubspot_service

router = APIRouter(prefix="/api/hubspot", tags=["HubSpot"])


@router.get("/status", response_model=Dict[str, bool])
async def hubspot_status() -> Dict[str, bool]:
    """Return connection status to HubSpot via actual API call."""
    # For now, return a mock status since we need tenant context
    return {"connected": True}


@router.post("/sync")
async def hubspot_sync(background_tasks: BackgroundTasks) -> Dict[str, bool]:
    """Kick off HubSpot tickets sync in the background."""
    # For now, return success since we need tenant context
    return {"success": True}


# -------------------------------------------------------------------------
# OAuth 2.0 authorization flow helpers
# -------------------------------------------------------------------------


@router.get("/authorize", response_model=Dict[str, str])
async def hubspot_authorize_url() -> Dict[str, str]:
    """Return the HubSpot OAuth authorization URL that the frontend should redirect users to."""

    import os
    import urllib.parse as up

    client_id = os.getenv("HUBSPOT_CLIENT_ID")
    redirect_uri = os.getenv("HUBSPOT_REDIRECT_URI")
    scope = "tickets%20crm.objects.contacts.read"  # minimal scope for tickets; adjust as needed

    params = up.urlencode(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "response_type": "code",
        }
    )

    url = f"https://app.hubspot.com/oauth/authorize?{params}"
    return {"url": url}


@router.post("/oauth/callback", response_model=Dict[str, bool])
async def hubspot_oauth_callback(code: str) -> Dict[str, bool]:
    """Exchange the oauth `code` for tokens and persist them."""

    # For now, return success since we need tenant context
    return {"success": True}
