from __future__ import annotations

import datetime as dt
from typing import Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.integration_token import IntegrationToken

HUBSPOT_TOKEN_URL = "https://api.hubapi.com/oauth/v1/token"

# ---------------------------------------------------------------------------
# HubSpot OAuth helpers (≤50 lines)
# ---------------------------------------------------------------------------


async def exchange_code(
    session: AsyncSession,
    provider: str,
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
) -> str:
    """Exchange a temporary OAuth `code` for tokens and persist them.

    Returns the *access token* string. Works for HubSpot at the moment but can
    be extended for other providers by switching on *provider*.
    """

    import httpx  # local import to avoid global dependency when unused

    data = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "code": code,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            HUBSPOT_TOKEN_URL,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        payload = resp.json()

    await save_or_update(
        session,
        provider,
        payload["access_token"],
        payload.get("refresh_token", ""),
        payload["expires_in"],
    )
    return payload["access_token"]


async def save_or_update(
    session: AsyncSession,
    provider: str,
    access_token: str,
    refresh_token: str,
    expires_in: int,
) -> None:
    """Insert or update the provider token row."""
    expires_at = dt.datetime.utcnow() + dt.timedelta(seconds=expires_in)

    token = IntegrationToken(
        provider=provider,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at,
    )
    session.merge(token)
    await session.commit()


async def get(session: AsyncSession, provider: str) -> Optional[IntegrationToken]:
    return await session.get(IntegrationToken, provider)


async def get_valid_access_token(
    session: AsyncSession,
    provider: str,
    client_id: str,
    client_secret: str,
) -> Optional[str]:
    """Return a non-expired access token; refresh automatically if needed."""
    token: Optional[IntegrationToken] = await session.get(IntegrationToken, provider)
    if token is None:
        return None

    # If token is still valid (>5 min buffer) return it
    if token.expires_at - dt.timedelta(minutes=5) > dt.datetime.utcnow():
        return token.access_token

    # Otherwise attempt refresh
    async with httpx.AsyncClient(timeout=30) as client:
        data = {
            "grant_type": "refresh_token",
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": token.refresh_token,
        }
        resp = await client.post(
            HUBSPOT_TOKEN_URL,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        payload = resp.json()

    token.access_token = payload["access_token"]
    token.refresh_token = payload.get("refresh_token", token.refresh_token)
    token.expires_at = dt.datetime.utcnow() + dt.timedelta(
        seconds=payload["expires_in"]
    )
    await session.commit()
    return token.access_token
