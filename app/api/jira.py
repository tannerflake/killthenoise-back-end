from __future__ import annotations

from typing import Dict

from fastapi import APIRouter

router = APIRouter(prefix="/api/jira", tags=["Jira"])


@router.post("/match-all")
async def jira_match_all() -> Dict[str, int | bool]:
    """Attempt to match all issues without Jira keys (stubbed)."""
    return {"success": True, "matched": 0} 