from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Query, Depends
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.issue import Issue

router = APIRouter(prefix="/api/issues", tags=["Issues"])


@router.get("/top")
async def get_top_issues(
    limit: int = Query(10, ge=1, le=100),
    session: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Return the top issues by severity/frequency."""
    try:
        # Query issues ordered by severity (desc) and frequency (desc)
        stmt = select(Issue).order_by(
            desc(Issue.severity),
            desc(Issue.frequency),
            desc(Issue.created_at)
        ).limit(limit)
        
        result = await session.execute(stmt)
        issues = result.scalars().all()
        
        # Convert to dict format
        issues_data = []
        for issue in issues:
            issues_data.append({
                "id": str(issue.id),
                "title": issue.title,
                "description": issue.description,
                "source": issue.source,
                "severity": issue.severity,
                "frequency": issue.frequency,
                "status": issue.status,
                "type": issue.type,
                "tags": issue.tags,
                "jira_issue_key": issue.jira_issue_key,
                "hubspot_ticket_id": issue.hubspot_ticket_id,
                "created_at": issue.created_at.isoformat() if issue.created_at else None,
                "updated_at": issue.updated_at.isoformat() if issue.updated_at else None
            })
        
        return {"success": True, "data": issues_data, "count": len(issues_data)}
    except Exception as e:
        return {"success": False, "error": str(e), "data": [], "count": 0}


@router.get("/")
async def list_issues(
    source: str | None = None,
    limit: int = Query(10, ge=1, le=100),
    session: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Return paginated list of issues filtered by optional source."""
    try:
        # Build query with optional source filter
        stmt = select(Issue)
        if source:
            stmt = stmt.where(Issue.source == source)
        
        stmt = stmt.order_by(desc(Issue.created_at)).limit(limit)
        
        result = await session.execute(stmt)
        issues = result.scalars().all()
        
        # Convert to dict format
        issues_data = []
        for issue in issues:
            issues_data.append({
                "id": str(issue.id),
                "title": issue.title,
                "description": issue.description,
                "source": issue.source,
                "severity": issue.severity,
                "frequency": issue.frequency,
                "status": issue.status,
                "type": issue.type,
                "tags": issue.tags,
                "jira_issue_key": issue.jira_issue_key,
                "hubspot_ticket_id": issue.hubspot_ticket_id,
                "created_at": issue.created_at.isoformat() if issue.created_at else None,
                "updated_at": issue.updated_at.isoformat() if issue.updated_at else None
            })
        
        return {"success": True, "data": issues_data, "count": len(issues_data)}
    except Exception as e:
        return {"success": False, "error": str(e), "data": [], "count": 0}
