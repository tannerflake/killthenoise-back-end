#!/usr/bin/env python3
"""HubSpot OAuth utility helpers.

This module provides `ensure_access_token` which guarantees there is a
`HUBSPOT_ACCESS_TOKEN` in the environment.  If none is present but client
credentials are, it guides the user through the public-app OAuth flow:

1. Constructs the install URL with `oauth tickets` scopes.
2. Opens the URL in the default browser.
3. Prompts the user to paste back the `code` from the redirect.
4. Exchanges the code for an access token via `https://api.hubapi.com/oauth/v1/token`.
5. Persists the access token to the `.env` file so subsequent runs work
   non-interactively.
"""
from __future__ import annotations

from pathlib import Path
import os
import sys
import webbrowser
from typing import Final

import httpx
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------
ENV_PATH: Final[Path] = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(ENV_PATH)

CLIENT_ID: Final[str | None] = os.getenv("HUBSPOT_CLIENT_ID")
CLIENT_SECRET: Final[str | None] = os.getenv("HUBSPOT_CLIENT_SECRET")
REDIRECT_URI: Final[str | None] = os.getenv("HUBSPOT_REDIRECT_URI")
SCOPES: Final[str] = "oauth tickets"

TOKEN_URL: Final[str] = "https://api.hubapi.com/oauth/v1/token"
INSTALL_URL_TMPL: Final[str] = (
    "https://app.hubspot.com/oauth/authorize?client_id={cid}&redirect_uri={uri}&scope="
    + SCOPES.replace(" ", "%20")
)

# ---------------------------------------------------------------------------
# Public helper
# ---------------------------------------------------------------------------


def ensure_access_token() -> str:  # noqa: D401
    """Return a valid access token, performing OAuth exchange if necessary."""
    access_token = os.getenv("HUBSPOT_ACCESS_TOKEN")
    if access_token:
        return access_token

    if not (CLIENT_ID and CLIENT_SECRET and REDIRECT_URI):
        print("❌ Missing HUBSPOT_CLIENT_ID / SECRET / REDIRECT_URI in .env")
        sys.exit(1)

    install_url = INSTALL_URL_TMPL.format(cid=CLIENT_ID, uri=REDIRECT_URI)
    print("🔗 Opening HubSpot install URL in your browser …")
    print(install_url)
    try:
        webbrowser.open(install_url)
    except Exception:  # pragma: no cover
        pass

    code = input("\nPaste the `code` value from the redirected URL: ").strip()
    if not code:
        print("❌ No code provided – aborting")
        sys.exit(1)

    print("🔄 Exchanging code for tokens …")
    data = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "code": code,
    }
    try:
        response = httpx.post(TOKEN_URL, data=data, timeout=15)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        print(f"❌ Token exchange failed: {exc.response.text}")
        sys.exit(1)

    tokens = response.json()
    access_token = tokens.get("access_token")
    if not access_token:
        print("❌ access_token missing from HubSpot response")
        sys.exit(1)

    _persist_token(access_token)
    print("✅ Access token saved to .env – you can now rerun without prompts")
    return access_token


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _persist_token(token: str) -> None:
    """Insert or update HUBSPOT_ACCESS_TOKEN in `.env`."""
    env_lines = ENV_PATH.read_text().splitlines() if ENV_PATH.exists() else []
    key = "HUBSPOT_ACCESS_TOKEN"
    replaced = False
    for i, line in enumerate(env_lines):
        if line.startswith(key + "="):
            env_lines[i] = f"{key}={token}"
            replaced = True
            break
    if not replaced:
        env_lines.append(f"{key}={token}")

    ENV_PATH.write_text("\n".join(env_lines) + "\n")


if __name__ == "__main__":  # pragma: no cover
    print(ensure_access_token()) 