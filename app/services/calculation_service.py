from __future__ import annotations

import datetime as dt
from typing import Dict, List, Any, Optional
from uuid import UUID
from collections import defaultdict, Counter

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.models.issue import Issue
from app.models.sync_event import SyncEvent


class CalculationService:
    """Service for calculating insights and metrics from synced data."""
    
    def __init__(self, tenant_id: UUID):
        self.tenant_id = tenant_id

    async def calculate_issue_metrics(self, time_range_days: int = 30) -> Dict[str, Any]:
        """Calculate comprehensive metrics for issues in the given time range."""
        async for session in get_db():
            since = dt.datetime.utcnow() - dt.timedelta(days=time_range_days)
            
            # Get issues in time range
            stmt = select(Issue).where(
                and_(
                    Issue.tenant_id == self.tenant_id,
                    Issue.created_at >= since
                )
            )
            result = await session.execute(stmt)
            issues = result.scalars().all()
            
            return self._calculate_metrics_from_issues(issues, time_range_days)

    async def calculate_source_comparison(self, time_range_days: int = 30) -> Dict[str, Any]:
        """Compare metrics across different data sources (HubSpot, Jira, etc.)."""
        async for session in get_db():
            since = dt.datetime.utcnow() - dt.timedelta(days=time_range_days)
            
            # Get issues grouped by source
            stmt = select(Issue).where(
                and_(
                    Issue.tenant_id == self.tenant_id,
                    Issue.created_at >= since
                )
            )
            result = await session.execute(stmt)
            issues = result.scalars().all()
            
            # Group by source
            source_groups = defaultdict(list)
            for issue in issues:
                source_groups[issue.source].append(issue)
            
            # Calculate metrics per source
            source_metrics = {}
            for source, source_issues in source_groups.items():
                source_metrics[source] = self._calculate_metrics_from_issues(
                    source_issues, time_range_days
                )
            
            return {
                "time_range_days": time_range_days,
                "sources": source_metrics,
                "total_issues": len(issues)
            }

    async def calculate_trends(self, days: int = 7) -> Dict[str, Any]:
        """Calculate daily trends for the past N days."""
        async for session in get_db():
            end_date = dt.datetime.utcnow()
            start_date = end_date - dt.timedelta(days=days)
            
            # Get daily counts
            stmt = select(
                func.date(Issue.created_at).label('date'),
                func.count(Issue.id).label('count')
            ).where(
                and_(
                    Issue.tenant_id == self.tenant_id,
                    Issue.created_at >= start_date,
                    Issue.created_at <= end_date
                )
            ).group_by(func.date(Issue.created_at)).order_by(func.date(Issue.created_at))
            
            result = await session.execute(stmt)
            daily_counts = result.all()
            
            # Convert to date: count mapping
            trends = {}
            for date, count in daily_counts:
                trends[date.isoformat()] = count
            
            return {
                "trends": trends,
                "total_days": days,
                "total_issues": sum(trends.values())
            }

    async def calculate_severity_distribution(self) -> Dict[str, Any]:
        """Calculate distribution of issues by severity level."""
        async for session in get_db():
            stmt = select(
                Issue.severity,
                func.count(Issue.id).label('count')
            ).where(
                and_(
                    Issue.tenant_id == self.tenant_id,
                    Issue.severity.isnot(None)
                )
            ).group_by(Issue.severity).order_by(Issue.severity.desc())
            
            result = await session.execute(stmt)
            severity_counts = result.all()
            
            distribution = {}
            total = 0
            for severity, count in severity_counts:
                distribution[f"level_{severity}"] = count
                total += count
            
            return {
                "distribution": distribution,
                "total": total,
                "severity_levels": {
                    5: "Critical",
                    4: "High", 
                    3: "Medium",
                    2: "Low",
                    1: "Minimal"
                }
            }

    async def calculate_status_distribution(self) -> Dict[str, Any]:
        """Calculate distribution of issues by status."""
        async for session in get_db():
            stmt = select(
                Issue.status,
                func.count(Issue.id).label('count')
            ).where(
                and_(
                    Issue.tenant_id == self.tenant_id,
                    Issue.status.isnot(None)
                )
            ).group_by(Issue.status)
            
            result = await session.execute(stmt)
            status_counts = result.all()
            
            distribution = {}
            total = 0
            for status, count in status_counts:
                if status:
                    distribution[status] = count
                    total += count
            
            return {
                "distribution": distribution,
                "total": total
            }

    async def calculate_sync_health(self, days: int = 7) -> Dict[str, Any]:
        """Calculate health metrics for sync operations."""
        async for session in get_db():
            since = dt.datetime.utcnow() - dt.timedelta(days=days)
            
            stmt = select(SyncEvent).where(
                and_(
                    SyncEvent.tenant_id == self.tenant_id,
                    SyncEvent.started_at >= since
                )
            ).order_by(SyncEvent.started_at.desc())
            
            result = await session.execute(stmt)
            sync_events = result.scalars().all()
            
            # Calculate sync health metrics
            total_syncs = len(sync_events)
            successful_syncs = len([e for e in sync_events if e.status == "success"])
            failed_syncs = len([e for e in sync_events if e.status == "failed"])
            
            avg_duration = 0
            if sync_events:
                durations = [e.duration_seconds for e in sync_events if e.duration_seconds]
                avg_duration = sum(durations) / len(durations) if durations else 0
            
            # Group by event type
            by_type = defaultdict(list)
            for event in sync_events:
                by_type[event.event_type].append(event)
            
            type_metrics = {}
            for event_type, events in by_type.items():
                success_rate = len([e for e in events if e.status == "success"]) / len(events)
                type_metrics[event_type] = {
                    "total": len(events),
                    "success_rate": success_rate,
                    "avg_duration": sum(e.duration_seconds or 0 for e in events) / len(events)
                }
            
            return {
                "total_syncs": total_syncs,
                "successful_syncs": successful_syncs,
                "failed_syncs": failed_syncs,
                "success_rate": successful_syncs / total_syncs if total_syncs > 0 else 0,
                "avg_duration_seconds": avg_duration,
                "by_type": type_metrics,
                "time_range_days": days
            }

    def _calculate_metrics_from_issues(self, issues: List[Issue], time_range_days: int) -> Dict[str, Any]:
        """Calculate metrics from a list of issues."""
        if not issues:
            return {
                "total_issues": 0,
                "avg_severity": 0,
                "status_distribution": {},
                "source_distribution": {},
                "recent_activity": 0
            }
        
        # Basic counts
        total_issues = len(issues)
        
        # Severity calculations
        severities = [i.severity for i in issues if i.severity is not None]
        avg_severity = sum(severities) / len(severities) if severities else 0
        
        # Status distribution
        status_counter = Counter(i.status for i in issues if i.status)
        status_distribution = dict(status_counter)
        
        # Source distribution
        source_counter = Counter(i.source for i in issues)
        source_distribution = dict(source_counter)
        
        # Recent activity (last 24 hours)
        recent_cutoff = dt.datetime.utcnow() - dt.timedelta(hours=24)
        recent_activity = len([i for i in issues if i.created_at >= recent_cutoff])
        
        # High priority issues (severity >= 4)
        high_priority = len([i for i in issues if i.severity and i.severity >= 4])
        
        return {
            "total_issues": total_issues,
            "avg_severity": round(avg_severity, 2),
            "status_distribution": status_distribution,
            "source_distribution": source_distribution,
            "recent_activity": recent_activity,
            "high_priority_count": high_priority,
            "time_range_days": time_range_days
        }

    async def get_top_issues(self, limit: int = 10, min_severity: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get top issues by severity and recency."""
        async for session in get_db():
            stmt = select(Issue).where(Issue.tenant_id == self.tenant_id)
            
            if min_severity is not None:
                stmt = stmt.where(Issue.severity >= min_severity)
            
            stmt = stmt.order_by(
                Issue.severity.desc().nullslast(),
                Issue.created_at.desc()
            ).limit(limit)
            
            result = await session.execute(stmt)
            issues = result.scalars().all()
            
            return [
                {
                    "id": str(issue.id),
                    "title": issue.title,
                    "severity": issue.severity,
                    "status": issue.status,
                    "source": issue.source,
                    "created_at": issue.created_at.isoformat(),
                    "description": issue.description
                }
                for issue in issues
            ]

    async def calculate_change_velocity(self, days: int = 30) -> Dict[str, Any]:
        """Calculate how quickly issues are being created and resolved."""
        async for session in get_db():
            since = dt.datetime.utcnow() - dt.timedelta(days=days)
            
            # Get issues created in time range
            stmt = select(Issue).where(
                and_(
                    Issue.tenant_id == self.tenant_id,
                    Issue.created_at >= since
                )
            ).order_by(Issue.created_at)
            
            result = await session.execute(stmt)
            issues = result.scalars().all()
            
            if not issues:
                return {
                    "creation_rate": 0,
                    "resolution_rate": 0,
                    "backlog_growth": 0,
                    "avg_time_to_resolution": 0
                }
            
            # Calculate creation rate (issues per day)
            creation_rate = len(issues) / days
            
            # Calculate resolution rate (assuming resolved issues have status 'resolved' or 'closed')
            resolved_issues = [i for i in issues if i.status in ['resolved', 'closed', 'done']]
            resolution_rate = len(resolved_issues) / days
            
            # Backlog growth rate
            backlog_growth = creation_rate - resolution_rate
            
            # Average time to resolution (simplified)
            resolution_times = []
            for issue in resolved_issues:
                if issue.updated_at and issue.created_at:
                    resolution_time = (issue.updated_at - issue.created_at).total_seconds() / 3600  # hours
                    resolution_times.append(resolution_time)
            
            avg_time_to_resolution = sum(resolution_times) / len(resolution_times) if resolution_times else 0
            
            return {
                "creation_rate": round(creation_rate, 2),
                "resolution_rate": round(resolution_rate, 2),
                "backlog_growth": round(backlog_growth, 2),
                "avg_time_to_resolution_hours": round(avg_time_to_resolution, 2),
                "total_created": len(issues),
                "total_resolved": len(resolved_issues),
                "time_range_days": days
            }


# Factory function for creating tenant-specific calculation services
def create_calculation_service(tenant_id: UUID) -> CalculationService:
    """Create a calculation service instance for a specific tenant."""
    return CalculationService(tenant_id) 