#!/usr/bin/env python3
"""hubspot_exchange_code.py

Exchange a HubSpot OAuth *authorization code* for an **access token** and
(optional) **refresh token**.

Usage
-----
1. Complete the OAuth flow in your browser and copy the `code` parameter from
   the redirect URL:

       http://localhost:5001/api/hubspot/callback?code=XXXXXXXX

2. Run:

       python3 scripts/hubspot_exchange_code.py <authorization_code>

3. The script prints the JSON response containing `access_token`,
   `refresh_token`, and `expires_in`.  Copy `access_token` into your `.env` as
   `HUBSPOT_ACCESS_TOKEN`.

Environment variables required
------------------------------
HUBSPOT_CLIENT_ID, HUBSPOT_CLIENT_SECRET, HUBSPOT_REDIRECT_URI must be set in
`.env` (they already are for this project).
"""
from __future__ import annotations

import json
import os
import sys
from typing import Final

import httpx
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID: Final[str | None] = os.getenv("HUBSPOT_CLIENT_ID")
CLIENT_SECRET: Final[str | None] = os.getenv("HUBSPOT_CLIENT_SECRET")
REDIRECT_URI: Final[str | None] = os.getenv("HUBSPOT_REDIRECT_URI")

if not all([CLIENT_ID, CLIENT_SECRET, REDIRECT_URI]):
    print(
        "❌ HUBSPOT_CLIENT_ID, HUBSPOT_CLIENT_SECRET, and HUBSPOT_REDIRECT_URI "
        "must be set in your .env file."
    )
    sys.exit(1)

if len(sys.argv) != 2:
    print("Usage: python3 scripts/hubspot_exchange_code.py <authorization_code>")
    sys.exit(1)

AUTH_CODE: Final[str] = sys.argv[1]

TOKEN_URL = "https://api.hubapi.com/oauth/v1/token"

async def exchange_code() -> None:  # noqa: D401
    """Exchange the temporary auth code for HubSpot tokens."""
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "redirect_uri": REDIRECT_URI,
                "code": AUTH_CODE,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:  # pragma: no cover
        print(f"❌ Failed to exchange code: {exc.response.text}")
        sys.exit(1)

    tokens = response.json()
    print("✅ Token exchange successful!\n")
    print(json.dumps(tokens, indent=2))

if __name__ == "__main__":  # pragma: no cover
    import asyncio

    asyncio.run(exchange_code()) 