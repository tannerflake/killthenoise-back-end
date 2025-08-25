from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Query, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.issue import Issue
from app.models.ai_issue_group import AIIssueGroup
from app.models.ai_issue_group_report import AIIssueGroupReport
from app.models.raw_report import RawReport
from app.models.tenant_integration import TenantIntegration
from app.services.ai_clustering_service import AIIssueClusteringService
from app.services.ai_clustering_service import _simple_signature

router = APIRouter(prefix="/api/issues", tags=["Issues"])


# Pydantic models for Jira ticket creation
class CreateJiraTicketRequest(BaseModel):
    title: str
    description: str


class CreateJiraTicketResponse(BaseModel):
    ticket_key: str
    ticket_url: str


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
                "source_id": issue.source_id,
                "severity": issue.severity,
                "frequency": issue.frequency,
                "status": issue.status,
                "type": issue.type,
                "tags": issue.tags,
                "jira_issue_key": issue.jira_issue_key,
                "jira_status": issue.jira_status,
                "jira_exists": issue.jira_exists,
                "ai_type_confidence": issue.ai_type_confidence,
                "ai_type_reasoning": issue.ai_type_reasoning,
                "created_at": issue.created_at.isoformat() if issue.created_at else None,
                "updated_at": issue.updated_at.isoformat() if issue.updated_at else None
            })
        
        return {"success": True, "data": issues_data, "count": len(issues_data)}
    except Exception as e:
        return {"success": False, "error": str(e), "data": [], "count": 0}


@router.get("/")
async def list_issues(
    source: str | None = None,
    team_id: str | None = None,
    limit: int = Query(10, ge=1, le=100),
    session: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """List AI-grouped issues (not raw individual issues)."""
    try:
        from sqlalchemy import desc
        from app.models.ai_issue_group import AIIssueGroup
        
        # Query AI issue groups instead of raw issues
        stmt = select(AIIssueGroup)
        
        # Apply filters
        if source:
            # Filter by source if specified
            stmt = stmt.where(AIIssueGroup.sources.contains([{"source": source}]))
        
        if team_id:
            # Filter by team if specified
            from uuid import UUID
            team_uuid = UUID(team_id)
            stmt = stmt.where(AIIssueGroup.team_id == team_uuid)
        
        stmt = stmt.order_by(desc(AIIssueGroup.updated_at)).limit(limit)
        
        result = await session.execute(stmt)
        groups = result.scalars().all()
        
        def clean_summary(summary: str | None) -> str | None:
            """Remove signature prefix from summary for frontend display."""
            if not summary:
                return None
            if summary.startswith("sig:") and "|" in summary:
                return summary.split("|", 1)[1]
            return summary
        
        data = []
        for group in groups:
            # Get the individual reports for this group to count them
            reports_stmt = select(AIIssueGroupReport).where(AIIssueGroupReport.group_id == group.id)
            reports_result = await session.execute(reports_stmt)
            reports = reports_result.scalars().all()
            
            data.append({
                "id": str(group.id),
                "title": group.title,
                "description": clean_summary(group.summary),
                "source": group.sources[0]["source"] if group.sources else "unknown",
                "severity": group.severity or 50,  # Default to 50 if not set
                "frequency": group.frequency,
                "status": group.status or "open",
                "type": "bug",  # Default type, could be enhanced later
                "tags": group.tags.split(",") if group.tags else [],
                "reports_count": len(reports),  # Number of individual reports in this group
                "sources": group.sources,
                "team_id": str(group.team_id) if group.team_id else None,
                "created_at": group.created_at.isoformat() if group.created_at else None,
                "updated_at": group.updated_at.isoformat() if group.updated_at else None
            })
        
        return {"success": True, "data": data, "count": len(data)}
        
    except Exception as e:
        return {"success": False, "error": str(e), "data": [], "count": 0}


# --------------------------- AI Issue Groups ---------------------------

@router.get("/ai")
async def list_ai_issue_groups(
    tenant_id: str | None = None,
    limit: int = Query(10, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    try:
        stmt = select(AIIssueGroup)
        if tenant_id:
            from uuid import UUID

            stmt = stmt.where(AIIssueGroup.tenant_id == UUID(tenant_id))
        stmt = stmt.order_by(desc(AIIssueGroup.updated_at)).limit(limit)

        result = await session.execute(stmt)
        groups = result.scalars().all()

        def clean_summary(summary: str | None) -> str | None:
            """Remove signature prefix from summary for frontend display."""
            if not summary:
                return None
            if summary.startswith("sig:") and "|" in summary:
                return summary.split("|", 1)[1]
            return summary

        data = [
            {
                "id": str(g.id),
                "tenant_id": str(g.tenant_id),
                "title": g.title,
                "summary": clean_summary(g.summary),
                "severity": g.severity,
                "tags": g.tags,
                "status": g.status,
                "frequency": g.frequency,
                "sources": g.sources,
                "updated_at": g.updated_at.isoformat() if g.updated_at else None,
            }
            for g in groups
        ]

        return {"success": True, "data": data, "count": len(data)}
    except Exception as e:
        return {"success": False, "error": str(e), "data": [], "count": 0}


@router.get("/ai/{group_id}/reports")
async def list_ai_issue_group_reports(
    group_id: str,
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    try:
        from uuid import UUID

        gid = UUID(group_id)
        # Join links -> reports
        link_stmt = select(AIIssueGroupReport).where(AIIssueGroupReport.group_id == gid)
        link_result = await session.execute(link_stmt)
        links = link_result.scalars().all()
        report_ids = [l.report_id for l in links]

        if not report_ids:
            return {"success": True, "data": [], "count": 0}

        report_stmt = select(RawReport).where(RawReport.id.in_(report_ids))
        report_result = await session.execute(report_stmt)
        reports = report_result.scalars().all()

        data = [
            {
                "id": str(r.id),
                "source": r.source,
                "external_id": r.external_id,
                "title": r.title,
                "url": r.url,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in reports
        ]

        return {"success": True, "data": data, "count": len(data)}
    except Exception as e:
        return {"success": False, "error": str(e), "data": [], "count": 0}


@router.post("/ai/recluster/{tenant_id}")
async def recluster_ai_issues(
    tenant_id: str,
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    from uuid import UUID

    service = AIIssueClusteringService(UUID(tenant_id), session)
    result = await service.recluster()
    return result


@router.post("/ai/cleanup-duplicates/{tenant_id}")
async def cleanup_duplicate_raw_reports(
    tenant_id: str,
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Remove duplicate raw reports, keeping only the most recent for each external_id."""
    try:
        from uuid import UUID
        from sqlalchemy import delete, func, desc
        from app.models.raw_report import RawReport
        from app.models.ai_issue_group_report import AIIssueGroupReport

        tenant_uuid = UUID(tenant_id)
        
        # Find duplicates (same tenant_id + source + external_id)
        duplicates_query = (
            select(
                RawReport.tenant_id,
                RawReport.source,
                RawReport.external_id,
                func.array_agg(RawReport.id.op('ORDER BY')(desc(RawReport.created_at))).label('ids'),
                func.count(RawReport.id).label('count')
            )
            .where(RawReport.tenant_id == tenant_uuid)
            .group_by(RawReport.tenant_id, RawReport.source, RawReport.external_id)
            .having(func.count(RawReport.id) > 1)
        )
        
        result = await session.execute(duplicates_query)
        duplicate_groups = result.all()
        
        removed_count = 0
        for group in duplicate_groups:
            ids_to_remove = group.ids[1:]  # Keep first (most recent), remove rest
            if ids_to_remove:
                # Remove group-report links first
                await session.execute(
                    delete(AIIssueGroupReport).where(AIIssueGroupReport.report_id.in_(ids_to_remove))
                )
                # Remove the duplicate reports
                await session.execute(
                    delete(RawReport).where(RawReport.id.in_(ids_to_remove))
                )
                removed_count += len(ids_to_remove)
        
        await session.commit()
        
        # Recluster after cleanup
        service = AIIssueClusteringService(tenant_uuid, session)
        recluster_result = await service.recluster()
        
        return {
            "success": True,
            "removed_duplicates": removed_count,
            "recluster_result": recluster_result
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/ai/test-raw-report/{tenant_id}")
async def test_create_raw_report(
    tenant_id: str,
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Test endpoint to manually create a raw report."""
    from uuid import UUID
    from app.services.ai_clustering_service import AIIssueClusteringService

    try:
        tid = UUID(tenant_id)
        clustering = AIIssueClusteringService(tid, session)
        
        # Create a test raw report
        report = await clustering.ingest_raw_report(
            source="test",
            external_id="test-123",
            title="Test HubSpot Ticket",
            body="This is a test ticket from HubSpot",
            url=None,
            commit=True
        )
        
        # Recluster to create AI issue group
        await clustering.recluster()
        
        return {
            "success": True,
            "report_id": str(report.id),
            "message": "Test raw report created successfully"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/ai/force-hubspot-sync/{tenant_id}")
async def force_hubspot_raw_reports(
    tenant_id: str,
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Force creation of raw reports from HubSpot tickets."""
    from uuid import UUID
    from app.services.ai_clustering_service import AIIssueClusteringService
    import httpx

    try:
        tid = UUID(tenant_id)
        
        # Get HubSpot tickets
        tickets_response = await httpx.AsyncClient().get(
            f"http://localhost:8000/api/hubspot/tickets/{tenant_id}/67aa21ad-b348-4b50-9333-b7b03c726d39"
        )
        tickets_data = tickets_response.json()
        
        if not tickets_data.get("success"):
            return {"success": False, "error": "Failed to fetch HubSpot tickets"}
        
        tickets = tickets_data.get("tickets", [])
        if not tickets:
            return {"success": False, "error": "No HubSpot tickets found"}
        
        # Create raw reports
        clustering = AIIssueClusteringService(tid, session)
        created_count = 0
        
        for ticket in tickets:
            props = ticket.get("properties", {})
            title = props.get("subject") or f"Ticket {ticket['id']}"
            body = props.get("content")
            
            await clustering.ingest_raw_report(
                source="hubspot",
                external_id=str(ticket["id"]),
                title=title,
                body=body,
                url=None,
                commit=False
            )
            created_count += 1
        
        await session.commit()
        
        # Recluster to create AI issue groups
        await clustering.recluster()
        
        return {
            "success": True,
            "created_raw_reports": created_count,
            "message": f"Created {created_count} raw reports from HubSpot tickets"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/ai/backfill/{tenant_id}")
async def backfill_raw_reports_from_issues(
    tenant_id: str,
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Backfill raw_reports from existing normalized issues (v1 utility).

    Creates one RawReport per Issue row for the tenant.
    """
    from uuid import UUID
    from app.services.ai_clustering_service import AIIssueClusteringService

    tid = UUID(tenant_id)

    try:
        # Get all issues (since current Issue model doesn't have tenant_id)
        result = await session.execute(select(Issue))
        issues = result.scalars().all()
        created = 0

        # Create AI clustering service
        clustering = AIIssueClusteringService(tid, session)

        for it in issues:
            try:
                title = it.title or ""
                body = it.description or None
                external_id = str(it.id)  # Use issue ID as external_id
                url = None

                # Create raw report using clustering service
                await clustering.ingest_raw_report(
                    source=it.source or "unknown",
                    external_id=external_id,
                    title=title,
                    body=body,
                    url=url,
                    commit=False  # Bulk insert without individual commits
                )
                created += 1
            except Exception as e:
                print(f"Error processing issue {it.id}: {e}")
                continue

        await session.commit()
        
        # Run clustering to create AI issue groups
        print("Running clustering...")
        clustering_result = await clustering.recluster()
        
        return {
            "success": True, 
            "created": created,
            "clustering_result": clustering_result
        }
    except Exception as e:
        await session.rollback()
        return {"success": False, "error": str(e)}


@router.post("/ai/{ai_issue_id}/create-jira-ticket")
async def create_jira_ticket_from_ai_issue(
    ai_issue_id: str,
    request: CreateJiraTicketRequest,
    tenant_id: str = Query(..., description="Tenant ID"),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Create a new Jira ticket from an AI issue group."""
    try:
        from uuid import UUID
        import httpx
        import base64
        import json
        from datetime import datetime

        tenant_uuid = UUID(tenant_id)
        ai_issue_uuid = UUID(ai_issue_id)

        # 1. Validate AI issue group exists and belongs to tenant
        ai_issue_query = select(AIIssueGroup).where(
            and_(
                AIIssueGroup.id == ai_issue_uuid,
                AIIssueGroup.tenant_id == tenant_uuid
            )
        )
        ai_issue_result = await session.execute(ai_issue_query)
        ai_issue = ai_issue_result.scalars().first()

        if not ai_issue:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "AI issue group not found",
                    "message": "The specified AI issue group was not found or doesn't belong to your tenant"
                }
            )

        # 2. Validate input
        if not request.title.strip():
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Invalid title",
                    "message": "Ticket title cannot be empty"
                }
            )

        if not request.description.strip():
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Invalid description", 
                    "message": "Ticket description cannot be empty"
                }
            )

        # 3. Get active Jira integration for the tenant
        jira_integration_query = select(TenantIntegration).where(
            and_(
                TenantIntegration.tenant_id == tenant_uuid,
                TenantIntegration.integration_type == "jira",
                TenantIntegration.is_active == True
            )
        )
        jira_result = await session.execute(jira_integration_query)
        jira_integration = jira_result.scalars().first()

        if not jira_integration:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "No Jira integration",
                    "message": "No active Jira integration found for your tenant. Please set up Jira integration first."
                }
            )

        # 4. Get Jira configuration
        config = jira_integration.config or {}
        base_url = config.get("base_url")
        access_token = config.get("access_token")
        email = config.get("email")

        if not base_url or not access_token:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Invalid Jira configuration",
                    "message": "Jira integration is not properly configured"
                }
            )

        # 5. Create Jira ticket via API
        jira_url = f"{base_url}/rest/api/3/issue"
        
        # Prepare auth header
        if access_token.startswith('ATATT') and email:
            # API token - use Basic Auth
            credentials = base64.b64encode(f"{email}:{access_token}".encode()).decode()
            auth_header = f"Basic {credentials}"
        else:
            # OAuth token
            auth_header = f"Bearer {access_token}"

        # Prepare Jira ticket payload
        jira_payload = {
            "fields": {
                "project": {
                    "key": "SCRUM"  # Default project - could be configurable
                },
                "summary": request.title.strip(),
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": request.description.strip()
                                }
                            ]
                        }
                    ]
                },
                "issuetype": {
                    "name": "Task"  # Default issue type - could be configurable
                }
            }
        }

        # Make API call to Jira
        async with httpx.AsyncClient() as client:
            response = await client.post(
                jira_url,
                headers={
                    "Authorization": auth_header,
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                json=jira_payload,
                timeout=30.0
            )

            if response.status_code not in [200, 201]:
                error_detail = "Unknown error"
                try:
                    error_response = response.json()
                    error_detail = error_response.get("errors", {}) or error_response.get("errorMessages", ["Unknown error"])
                except:
                    error_detail = f"HTTP {response.status_code}: {response.text[:200]}"

                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": "Jira API error",
                        "message": f"Failed to create Jira ticket: {error_detail}"
                    }
                )

            jira_response = response.json()
            ticket_key = jira_response.get("key")
            
            if not ticket_key:
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": "Invalid Jira response",
                        "message": "Jira API didn't return a ticket key"
                    }
                )

        # 6. Create raw report linking AI issue to Jira ticket
        ticket_url = f"{base_url}/browse/{ticket_key}"
        
        # Use the AI clustering service to create the link
        clustering_service = AIIssueClusteringService(tenant_uuid, session)
        new_report = await clustering_service.ingest_raw_report(
            source="jira",
            external_id=ticket_key,
            title=request.title.strip(),
            body=request.description.strip(),
            url=ticket_url,
            commit=False
        )

        # Link the new report to the AI issue group
        link = AIIssueGroupReport(group_id=ai_issue.id, report_id=new_report.id)
        session.add(link)

        # Update AI issue group frequency and sources
        ai_issue.frequency += 1
        sources = list(ai_issue.sources) if ai_issue.sources else []
        
        # Update Jira count in sources
        jira_source_found = False
        for source in sources:
            if source.get("source") == "jira":
                source["count"] = source.get("count", 0) + 1
                jira_source_found = True
                break
        
        if not jira_source_found:
            sources.append({"source": "jira", "count": 1})
        
        ai_issue.sources = sources

        await session.commit()

        return {
            "success": True,
            "data": {
                "ticket_key": ticket_key,
                "ticket_url": ticket_url
            },
            "message": "Jira ticket created successfully"
        }

    except HTTPException:
        await session.rollback()
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Internal server error",
                "message": f"An unexpected error occurred: {str(e)}"
            }
        )
