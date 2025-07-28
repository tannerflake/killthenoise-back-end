from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/issues", tags=["Issues"])


@router.get("/top")
async def get_top_issues(limit: int = Query(10, ge=1, le=100)) -> Dict[str, Any]:
    """Return the top issues by severity/frequency (stubbed)."""
    return {"success": True, "data": [], "count": 0}


@router.get("/")
async def list_issues(
    source: str | None = None,
    limit: int = Query(10, ge=1, le=100),
) -> Dict[str, Any]:
    """Return paginated list of issues filtered by optional source (stubbed)."""
    return {"success": True, "data": [], "count": 0} 