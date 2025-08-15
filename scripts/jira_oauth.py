#!/usr/bin/env python3
"""
Simple Jira OAuth (3LO) helper.

- Opens the Atlassian authorize URL in your browser
- Prompts you to paste the returned `code`
- Exchanges it for an access token
- Saves `JIRA_ACCESS_TOKEN` into `.env`

Prereqs: JIRA_CLIENT_ID, JIRA_CLIENT_SECRET, JIRA_REDIRECT_URI in `.env`.
Recommended scopes:
  offline_access read:jira-user read:jira-work write:jira-work
"""

from __future__ import annotations

import os
import sys
import urllib.parse
import webbrowser
from pathlib import Path
from typing import Final

import httpx
from dotenv import load_dotenv

ENV_PATH: Final[Path] = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(ENV_PATH)

CLIENT_ID: Final[str | None] = os.getenv("JIRA_CLIENT_ID")
CLIENT_SECRET: Final[str | None] = os.getenv("JIRA_CLIENT_SECRET")
REDIRECT_URI: Final[str | None] = os.getenv("JIRA_REDIRECT_URI")

AUTH_URL: Final[str] = "https://auth.atlassian.com/authorize"
TOKEN_URL: Final[str] = "https://auth.atlassian.com/oauth/token"
AUDIENCE: Final[str] = "api.atlassian.com"
SCOPES: Final[str] = "offline_access read:jira-user read:jira-work write:jira-work"


def _persist_token(token: str) -> None:
	"""Insert or update JIRA_ACCESS_TOKEN in `.env`."""
	env_lines = ENV_PATH.read_text().splitlines() if ENV_PATH.exists() else []
	key = "JIRA_ACCESS_TOKEN"
	replaced = False
	for i, line in enumerate(env_lines):
		if line.startswith(key + "="):
			env_lines[i] = f"{key}={token}"
			replaced = True
			break
	if not replaced:
		env_lines.append(f"{key}={token}")
	ENV_PATH.write_text("\n".join(env_lines) + "\n")


def ensure_access_token() -> str:
	"""Return a valid Jira access token, guiding through OAuth if needed."""
	existing = os.getenv("JIRA_ACCESS_TOKEN")
	if existing:
		return existing

	if not (CLIENT_ID and CLIENT_SECRET and REDIRECT_URI):
		print("❌ Missing JIRA_CLIENT_ID / JIRA_CLIENT_SECRET / JIRA_REDIRECT_URI in .env")
		sys.exit(1)

	params = {
		"audience": AUDIENCE,
		"client_id": CLIENT_ID,
		"scope": SCOPES,
		"redirect_uri": REDIRECT_URI,
		"state": "dev-local",  # optional static state for local use
		"response_type": "code",
		"prompt": "consent",
	}
	auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"

	print("🔗 Opening Jira authorize URL in your browser …")
	print(auth_url)
	try:
		webbrowser.open(auth_url)
	except Exception:
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
		resp = httpx.post(TOKEN_URL, json=data, timeout=20)
		resp.raise_for_status()
	except httpx.HTTPError as exc:
		print(f"❌ Token exchange failed: {exc.response.text if exc.response else exc}")
		sys.exit(1)

	payload = resp.json()
	token = payload.get("access_token")
	if not token:
		print("❌ access_token missing from Atlassian response")
		sys.exit(1)

	_persist_token(token)
	print("✅ Access token saved to .env as JIRA_ACCESS_TOKEN")
	return token


if __name__ == "__main__":  # pragma: no cover
	print(ensure_access_token())
