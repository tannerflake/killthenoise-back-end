from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Path, Query
from pydantic import BaseModel

from app.services.calculation_service import create_calculation_service

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


class AnalyticsRequest(BaseModel):
    tenant_id: UUID
    time_range_days: int = 30
    min_severity: Optional[int] = None


@router.get("/metrics/{tenant_id}")
async def get_issue_metrics(
    tenant_id: UUID = Path(..., description="Tenant ID"),
    time_range_days: int = Query(30, ge=1, le=365, description="Time range in days"),
) -> Dict[str, Any]:
    """Get comprehensive issue metrics for a tenant."""
    calc_service = create_calculation_service(tenant_id)
    return await calc_service.calculate_issue_metrics(time_range_days)


@router.get("/source-comparison/{tenant_id}")
async def get_source_comparison(
    tenant_id: UUID = Path(..., description="Tenant ID"),
    time_range_days: int = Query(30, ge=1, le=365, description="Time range in days"),
) -> Dict[str, Any]:
    """Compare metrics across different data sources (HubSpot, Jira, etc.)."""
    calc_service = create_calculation_service(tenant_id)
    return await calc_service.calculate_source_comparison(time_range_days)


@router.get("/trends/{tenant_id}")
async def get_trends(
    tenant_id: UUID = Path(..., description="Tenant ID"),
    days: int = Query(7, ge=1, le=90, description="Number of days to analyze"),
) -> Dict[str, Any]:
    """Get daily trends for the past N days."""
    calc_service = create_calculation_service(tenant_id)
    return await calc_service.calculate_trends(days)


@router.get("/severity-distribution/{tenant_id}")
async def get_severity_distribution(
    tenant_id: UUID = Path(..., description="Tenant ID")
) -> Dict[str, Any]:
    """Get distribution of issues by severity level."""
    calc_service = create_calculation_service(tenant_id)
    return await calc_service.calculate_severity_distribution()


@router.get("/status-distribution/{tenant_id}")
async def get_status_distribution(
    tenant_id: UUID = Path(..., description="Tenant ID")
) -> Dict[str, Any]:
    """Get distribution of issues by status."""
    calc_service = create_calculation_service(tenant_id)
    return await calc_service.calculate_status_distribution()


@router.get("/top-issues/{tenant_id}")
async def get_top_issues(
    tenant_id: UUID = Path(..., description="Tenant ID"),
    limit: int = Query(10, ge=1, le=100, description="Number of issues to return"),
    min_severity: Optional[int] = Query(
        None, ge=1, le=5, description="Minimum severity level"
    ),
) -> List[Dict[str, Any]]:
    """Get top issues by severity and recency."""
    calc_service = create_calculation_service(tenant_id)
    return await calc_service.get_top_issues(limit, min_severity)


@router.get("/change-velocity/{tenant_id}")
async def get_change_velocity(
    tenant_id: UUID = Path(..., description="Tenant ID"),
    days: int = Query(30, ge=1, le=365, description="Time range in days"),
) -> Dict[str, Any]:
    """Calculate how quickly issues are being created and resolved."""
    calc_service = create_calculation_service(tenant_id)
    return await calc_service.calculate_change_velocity(days)


@router.get("/dashboard/{tenant_id}")
async def get_dashboard_data(
    tenant_id: UUID = Path(..., description="Tenant ID"),
    time_range_days: int = Query(30, ge=1, le=365, description="Time range in days"),
) -> Dict[str, Any]:
    """Get comprehensive dashboard data including all key metrics."""
    calc_service = create_calculation_service(tenant_id)

    # Gather all metrics in parallel
    import asyncio

    tasks = [
        calc_service.calculate_issue_metrics(time_range_days),
        calc_service.calculate_source_comparison(time_range_days),
        calc_service.calculate_trends(7),  # Last 7 days for trends
        calc_service.calculate_severity_distribution(),
        calc_service.calculate_status_distribution(),
        calc_service.get_top_issues(10),
        calc_service.calculate_change_velocity(time_range_days),
    ]

    results = await asyncio.gather(*tasks)

    return {
        "tenant_id": str(tenant_id),
        "time_range_days": time_range_days,
        "metrics": results[0],
        "source_comparison": results[1],
        "trends": results[2],
        "severity_distribution": results[3],
        "status_distribution": results[4],
        "top_issues": results[5],
        "change_velocity": results[6],
    }
