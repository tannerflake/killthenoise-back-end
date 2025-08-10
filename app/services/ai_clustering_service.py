from __future__ import annotations

import hashlib
from collections import defaultdict
from typing import Any, Dict, List, Tuple
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.raw_report import RawReport
from app.models.ai_issue_group import AIIssueGroup
from app.models.ai_issue_group_report import AIIssueGroupReport


def _simple_signature(title: str, body: str | None) -> str:
    """Create a stable signature for clustering (v1 heuristic).

    Lowercase, strip whitespace, take first 200 chars, hash.
    """
    text = (title or "") + "\n" + (body or "")
    key = " ".join(text.lower().split())[:200]
    return hashlib.sha256(key.encode()).hexdigest()[:24]


class AIIssueClusteringService:
    """Cluster raw reports into AI issue groups per tenant.

    v1 uses deterministic string signatures to group likely duplicates.
    """

    def __init__(self, tenant_id: UUID, session: AsyncSession) -> None:
        self.tenant_id = tenant_id
        self.session = session

    async def ingest_raw_report(self, *, source: str, external_id: str | None, title: str, body: str | None, url: str | None, commit: bool = True) -> RawReport:
        # Check if report already exists (deduplication)
        if external_id:
            existing_query = select(RawReport).where(
                and_(
                    RawReport.tenant_id == self.tenant_id,
                    RawReport.source == source,
                    RawReport.external_id == external_id
                )
            )
            result = await self.session.execute(existing_query)
            existing_report = result.scalars().first()
            
            if existing_report:
                # Update existing report with latest data
                existing_report.title = title
                existing_report.body = body
                existing_report.url = url
                existing_report.signature = _simple_signature(title, body)
                if commit:
                    await self.session.commit()
                    await self.session.refresh(existing_report)
                return existing_report

        # Create new report if not found
        signature = _simple_signature(title, body)
        report = RawReport(
            tenant_id=self.tenant_id,
            source=source,
            external_id=external_id,
            title=title,
            body=body,
            url=url,
            signature=signature,
        )
        self.session.add(report)
        if commit:
            await self.session.commit()
            await self.session.refresh(report)
        else:
            await self.session.flush()  # Get the ID without committing
        return report

    async def recluster(self) -> Dict[str, Any]:
        # Load reports
        q = await self.session.execute(
            select(RawReport).where(RawReport.tenant_id == self.tenant_id)
        )
        reports: List[RawReport] = q.scalars().all()

        # Group by signature
        sig_to_reports: Dict[str, List[RawReport]] = defaultdict(list)
        for r in reports:
            if r.signature:
                sig_to_reports[r.signature].append(r)

        created, updated = 0, 0
        for sig, items in sig_to_reports.items():
            # Generate AI-powered title and summary for this group
            title, summary = await self._summarize_group(items)

            # Find existing group by signature stored in summary field (hack for v1)
            # We'll store the signature in a new field later, for now use a prefix
            signature_marker = f"sig:{sig}"
            existing = await self.session.execute(
                select(AIIssueGroup).where(
                    and_(
                        AIIssueGroup.tenant_id == self.tenant_id,
                        AIIssueGroup.summary.like(f"{signature_marker}%")
                    )
                )
            )
            group = existing.scalars().first()

            if not group:
                # Store signature in summary with prefix for lookup
                summary_with_sig = f"sig:{sig}|{summary}" if summary else f"sig:{sig}"
                group = AIIssueGroup(
                    tenant_id=self.tenant_id,
                    title=title,
                    summary=summary_with_sig,
                    severity=None,
                    tags=None,
                    status="open",
                    frequency=0,
                    sources=[],
                )
                self.session.add(group)
                await self.session.flush()  # Get the group ID
                created += 1
            else:
                # Update existing group with new AI-generated title and summary
                group.title = title
                summary_with_sig = f"sig:{sig}|{summary}" if summary else f"sig:{sig}"
                group.summary = summary_with_sig
                updated += 1

            # Clear existing links for this group first
            from sqlalchemy import delete
            await self.session.execute(
                delete(AIIssueGroupReport).where(AIIssueGroupReport.group_id == group.id)
            )

            # Ensure link rows
            seen_report_ids = set()
            for item in items:
                link = AIIssueGroupReport(group_id=group.id, report_id=item.id)
                self.session.add(link)
                seen_report_ids.add(item.id)

            # Update rollups
            group.frequency = len(items)
            source_counts: Dict[str, int] = defaultdict(int)
            for item in items:
                source_counts[item.source] += 1
            group.sources = [{"source": s, "count": c} for s, c in source_counts.items()]

        # Clean up orphaned groups (groups with no linked reports)
        from sqlalchemy import delete
        orphaned_groups_query = select(AIIssueGroup.id).where(
            and_(
                AIIssueGroup.tenant_id == self.tenant_id,
                ~AIIssueGroup.id.in_(
                    select(AIIssueGroupReport.group_id).distinct()
                )
            )
        )
        orphaned_result = await self.session.execute(orphaned_groups_query)
        orphaned_ids = [row[0] for row in orphaned_result]
        
        if orphaned_ids:
            await self.session.execute(
                delete(AIIssueGroup).where(AIIssueGroup.id.in_(orphaned_ids))
            )
            print(f"[AI_CLUSTERING] Cleaned up {len(orphaned_ids)} orphaned groups")

        await self.session.commit()
        return {"success": True, "created": created, "updated": updated, "groups": len(sig_to_reports)}

    async def _summarize_group(self, reports: List[RawReport]) -> Tuple[str, str]:
        """Generate AI summary for a group of reports using Claude."""
        import os
        import httpx
        
        # Get Claude API key from environment
        claude_api_key = os.getenv("CLAUDE_API_KEY")
        if not claude_api_key:
            # Fallback to simple summarization
            title = reports[0].title or "Untitled Issue"
            descriptions = [r.body for r in reports if r.body]
            summary = " | ".join(descriptions[:3]) if descriptions else None
            return title, summary
        
        # Prepare context for Claude
        report_context = []
        for i, report in enumerate(reports[:5], 1):  # Limit to 5 reports to avoid token limits
            context = f"Report {i} (from {report.source}):\n"
            context += f"Title: {report.title or 'No title'}\n"
            if report.body:
                context += f"Description: {report.body[:500]}...\n"  # Truncate long descriptions
            context += f"URL: {report.url or 'No URL'}\n\n"
            report_context.append(context)
        
        reports_text = "".join(report_context)
        
        prompt = f"""You are analyzing multiple issue reports that appear to be related. Please provide:

1. A concise, descriptive title (max 80 characters) that captures the common theme
2. A brief summary (max 200 characters) explaining what the issue is about

Here are the reports:

{reports_text}

Respond in JSON format:
{{
    "title": "Your generated title here",
    "summary": "Your generated summary here"
}}"""

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": claude_api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json"
                    },
                    json={
                        "model": "claude-3-haiku-20240307",
                        "max_tokens": 300,
                        "messages": [
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ]
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result["content"][0]["text"]
                    
                    # Parse JSON response
                    import json
                    try:
                        ai_result = json.loads(content)
                        title = ai_result.get("title", reports[0].title or "AI-Generated Issue")
                        summary = ai_result.get("summary", None)
                        return title, summary
                    except json.JSONDecodeError:
                        # If JSON parsing fails, extract title and summary manually
                        lines = content.split('\n')
                        title = reports[0].title or "AI-Generated Issue"
                        summary = content[:200] if content else None
                        return title, summary
                        
        except Exception as e:
            print(f"[AI_CLUSTERING] Claude API error: {e}")
            
        # Fallback to simple summarization
        title = reports[0].title or "Fallback Issue"
        descriptions = [r.body for r in reports if r.body]
        summary = " | ".join(descriptions[:3]) if descriptions else None
        return title, summary

