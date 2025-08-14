#!/usr/bin/env python3
"""
Create Jira issues from AI-generated JSON (Jira only)

- Ensures a Jira access token via scripts/jira_oauth.py (opens browser, paste code)
- Reads latest ai_generated_issues_*.json
- Creates up to N Jira issues in a selected project
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


def ensure_jira_access_token() -> Optional[str]:
    try:
        from scripts.jira_oauth import ensure_access_token as _ensure
        return _ensure()
    except SystemExit:
        return None
    except Exception as e:
        logger.error(f"Jira OAuth failed: {e}")
        return None


def _map_priority(sev: int) -> str:
    return {1: "Lowest", 2: "Low", 3: "Medium", 4: "High", 5: "Highest"}.get(sev, "Medium")


def _map_issue_type(issue: Dict[str, Any]) -> str:
    t = (issue.get("type") or "").lower()
    if t in {"bug", "performance", "security"}:
        return "Bug"
    if "feature" in t:
        return "Story"
    return "Task"


async def _discover_cloud_and_project(client: httpx.AsyncClient, token: str) -> Optional[str]:
    res = await client.get(
        "https://api.atlassian.com/oauth/token/accessible-resources",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    if res.status_code != 200:
        logger.error(f"Jira resources failed: {res.status_code} {res.text}")
        return None
    resources = res.json()
    if not resources:
        logger.error("No Jira cloud resources accessible for this token")
        return None
    cloud_id = resources[0]["id"]

    # Pick project: prefer env var, else first available
    preferred = os.getenv("JIRA_PROJECT_KEY")
    proj_res = await client.get(
        f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/project",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    project_key = None
    if proj_res.status_code == 200:
        projects = proj_res.json() or []
        if preferred and any(p.get("key") == preferred for p in projects):
            project_key = preferred
        elif projects:
            project_key = projects[0].get("key")
    project_key = project_key or preferred or "TEST"

    return f"{cloud_id}:{project_key}"


async def create_jira_issue(token: str, cloud_id: str, project_key: str, issue: Dict[str, Any]) -> Optional[str]:
    payload = {
        "fields": {
            "project": {"key": project_key},
            "summary": issue["title"],
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {"type": "paragraph", "content": [{"type": "text", "text": issue["description"]}]}
                ],
            },
            "issuetype": {"name": _map_issue_type(issue)},
            "priority": {"name": _map_priority(issue.get("severity", 3))},
        }
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/issue",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        if resp.status_code == 201:
            return resp.json().get("key")
        logger.error(f"Jira create failed: {resp.status_code} {resp.text}")
        return None


async def main() -> None:
    print("🚀 Create Jira Issues from AI-generated JSON")
    print("=" * 60)

    token = ensure_jira_access_token()
    if not token:
        print("❌ Could not obtain Jira access token")
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
    jira_issues = [i for i in all_issues if i.get("source") == "jira"]
    if not jira_issues:
        print("⚠️ No Jira issues found in the JSON – nothing to create")
        return

    # Limit to 5 for safety
    to_create = jira_issues[:5]

    async with httpx.AsyncClient(timeout=30.0) as client:
        info = await _discover_cloud_and_project(client, token)
    if not info:
        print("❌ Could not determine Jira cloud/project")
        return
    cloud_id, project_key = info.split(":", 1)
    print(f"🧭 Target project: {project_key} (cloud {cloud_id[:8]}…)")

    created = 0
    for idx, issue in enumerate(to_create, 1):
        print(f"📝 [{idx}/{len(to_create)}] {issue['title']}")
        key = await create_jira_issue(token, cloud_id, project_key, issue)
        if key:
            created += 1
            print(f"   ✅ Created Jira issue: {key}")
        else:
            print("   ❌ Failed to create issue")

    print("\n" + "=" * 40)
    print("📊 Done")
    print(f"Created: {created} / {len(to_create)}")


if __name__ == "__main__":
    asyncio.run(main())
