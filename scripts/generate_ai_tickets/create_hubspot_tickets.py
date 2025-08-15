#!/usr/bin/env python3
"""
Create HubSpot tickets from AI-generated issues (HubSpot only)

- Ensures a HubSpot access token via scripts/hubspot_oauth.py
- Reads latest ai_generated_issues_*.json
- Creates up to N HubSpot tickets
"""

from __future__ import annotations

import asyncio
import glob
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def ensure_hubspot_access_token() -> Optional[str]:
    try:
        from scripts.hubspot_oauth import ensure_access_token as _ensure
        return _ensure()
    except SystemExit:
        return None
    except Exception as e:
        logger.error(f"HubSpot OAuth failed: {e}")
        return None


def _map_severity_to_hubspot_priority(sev: int) -> str:
    return {1: "LOW", 2: "LOW", 3: "MEDIUM", 4: "HIGH", 5: "URGENT"}.get(sev, "MEDIUM")


def _map_category_to_hubspot(issue: Dict[str, Any]) -> str:
    t = (issue.get("type") or "").lower()
    tags = (issue.get("tags") or "").lower()
    if "feature" in t or "feature" in tags:
        return "FEATURE_REQUEST"
    if "billing" in t or "billing" in tags or "invoice" in tags:
        return "BILLING_ISSUE"
    if t in {"bug", "performance", "security"} or any(x in tags for x in ["bug", "error", "crash", "security", "performance"]):
        return "PRODUCT_ISSUE"
    return "GENERAL_INQUIRY"


async def create_hubspot_ticket(access_token: str, issue: Dict[str, Any]) -> Optional[str]:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            payload = {
                "properties": {
                    "subject": issue["title"],
                    "content": issue["description"],
                    "hs_ticket_priority": _map_severity_to_hubspot_priority(issue.get("severity", 3)),
                    "hs_ticket_category": _map_category_to_hubspot(issue),
                    # Default pipeline/stage values expected by HubSpot
                    "hs_pipeline": "0",
                    "hs_pipeline_stage": "1",
                }
            }
            resp = await client.post(
                "https://api.hubapi.com/crm/v3/objects/tickets",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            if resp.status_code == 201:
                return str(resp.json().get("id"))
            logger.error(f"HubSpot create failed: {resp.status_code} {resp.text}")
            return None
    except Exception as e:
        logger.error(f"HubSpot create error: {e}")
        return None


async def main() -> None:
    print("🚀 Create HubSpot Tickets from AI-generated issues")
    print("=" * 60)

    # Ensure token (opens browser and prompts for code if needed)
    token = ensure_hubspot_access_token()
    if not token:
        print("❌ Could not obtain HubSpot access token")
        return

    files = sorted(glob.glob("ai_generated_issues_*.json"), key=os.path.getctime)
    if not files:
        print("❌ No ai_generated_issues_*.json found. Run scripts/test_ai_generation_output.py first.")
        return

    latest = files[-1]
    print(f"📄 Using: {latest}")

    with open(latest, "r") as f:
        data = json.load(f)

    all_issues: List[Dict[str, Any]] = data.get("issues", [])
    hubspot_issues = [i for i in all_issues if i.get("source") == "hubspot"]
    if not hubspot_issues:
        print("⚠️ No HubSpot issues found in the JSON – nothing to create")
        return

    # Limit to 5 for safety
    to_create = hubspot_issues[:5]
    print(f"🎯 Will create {len(to_create)} HubSpot tickets")

    created = 0
    for idx, issue in enumerate(to_create, 1):
        print(f"📝 [{idx}/{len(to_create)}] {issue['title']}")
        ticket_id = await create_hubspot_ticket(token, issue)
        if ticket_id:
            created += 1
            print(f"   ✅ Created HubSpot ticket ID: {ticket_id}")
        else:
            print("   ❌ Failed to create ticket")

    print("\n" + "=" * 40)
    print("📊 Done")
    print(f"Created: {created} / {len(to_create)}")


if __name__ == "__main__":
    asyncio.run(main())
