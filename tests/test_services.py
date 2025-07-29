from __future__ import annotations

import datetime as dt
import uuid
from typing import Dict, Any
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.calculation_service import CalculationService
from app.services.hubspot_service import HubSpotService
from app.services.scheduler_service import SchedulerService
from app.models.issue import Issue
from app.models.tenant_integration import TenantIntegration
from app.models.sync_event import SyncEvent


class TestCalculationService:
    """Test calculation service business logic."""

    @pytest.mark.asyncio
    async def test_calculate_issue_metrics_empty_data(self, db_session: AsyncSession):
        """Test metrics calculation with no issues."""
        tenant_id = uuid.uuid4()
        calc_service = CalculationService(tenant_id)
        
        result = await calc_service.calculate_issue_metrics(time_range_days=30)
        
        assert result["total_issues"] == 0
        assert result["avg_severity"] == 0
        assert result["status_distribution"] == {}
        assert result["source_distribution"] == {}

    @pytest.mark.asyncio
    async def test_calculate_issue_metrics_with_data(self, db_session: AsyncSession):
        """Test metrics calculation with sample issues."""
        tenant_id = uuid.uuid4()
        
        # Create sample issues
        issues = [
            Issue(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                title="High Priority Issue",
                source="hubspot",
                severity=5,
                status="open"
            ),
            Issue(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                title="Medium Priority Issue",
                source="jira",
                severity=3,
                status="resolved"
            )
        ]
        
        for issue in issues:
            db_session.add(issue)
        await db_session.commit()
        
        calc_service = CalculationService(tenant_id)
        result = await calc_service.calculate_issue_metrics(time_range_days=30)
        
        assert result["total_issues"] == 2
        assert result["avg_severity"] == 4.0
        assert "hubspot" in result["source_distribution"]
        assert "jira" in result["source_distribution"]
        assert "open" in result["status_distribution"]
        assert "resolved" in result["status_distribution"]

    @pytest.mark.asyncio
    async def test_calculate_source_comparison(self, db_session: AsyncSession):
        """Test source comparison calculation."""
        tenant_id = uuid.uuid4()
        
        # Create issues from different sources
        issues = [
            Issue(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                title="HubSpot Issue",
                source="hubspot",
                severity=4
            ),
            Issue(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                title="Jira Issue",
                source="jira",
                severity=3
            )
        ]
        
        for issue in issues:
            db_session.add(issue)
        await db_session.commit()
        
        calc_service = CalculationService(tenant_id)
        result = await calc_service.calculate_source_comparison(time_range_days=30)
        
        assert "sources" in result
        assert "hubspot" in result["sources"]
        assert "jira" in result["sources"]
        assert result["total_issues"] == 2

    @pytest.mark.asyncio
    async def test_calculate_trends(self, db_session: AsyncSession):
        """Test trend calculation."""
        tenant_id = uuid.uuid4()
        
        # Create issues with different dates
        today = dt.datetime.utcnow()
        yesterday = today - dt.timedelta(days=1)
        
        issues = [
            Issue(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                title="Today's Issue",
                source="hubspot",
                created_at=today
            ),
            Issue(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                title="Yesterday's Issue",
                source="jira",
                created_at=yesterday
            )
        ]
        
        for issue in issues:
            db_session.add(issue)
        await db_session.commit()
        
        calc_service = CalculationService(tenant_id)
        result = await calc_service.calculate_trends(days=7)
        
        assert "trends" in result
        assert result["total_days"] == 7
        assert result["total_issues"] == 2

    @pytest.mark.asyncio
    async def test_get_top_issues(self, db_session: AsyncSession):
        """Test getting top issues by severity."""
        tenant_id = uuid.uuid4()
        
        # Create issues with different severities
        issues = [
            Issue(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                title="Critical Issue",
                source="hubspot",
                severity=5
            ),
            Issue(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                title="Low Priority Issue",
                source="jira",
                severity=2
            )
        ]
        
        for issue in issues:
            db_session.add(issue)
        await db_session.commit()
        
        calc_service = CalculationService(tenant_id)
        result = await calc_service.get_top_issues(limit=10)
        
        assert len(result) == 2
        # Should be ordered by severity (highest first)
        assert result[0]["severity"] == 5
        assert result[1]["severity"] == 2

    @pytest.mark.asyncio
    async def test_calculate_change_velocity(self, db_session: AsyncSession):
        """Test change velocity calculation."""
        tenant_id = uuid.uuid4()
        
        # Create resolved issues
        today = dt.datetime.utcnow()
        yesterday = today - dt.timedelta(days=1)
        
        issues = [
            Issue(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                title="Created Today",
                source="hubspot",
                created_at=today,
                status="open"
            ),
            Issue(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                title="Resolved Issue",
                source="jira",
                created_at=yesterday,
                status="resolved",
                updated_at=today
            )
        ]
        
        for issue in issues:
            db_session.add(issue)
        await db_session.commit()
        
        calc_service = CalculationService(tenant_id)
        result = await calc_service.calculate_change_velocity(days=30)
        
        assert "creation_rate" in result
        assert "resolution_rate" in result
        assert "backlog_growth" in result
        assert result["total_created"] == 2
        assert result["total_resolved"] == 1


class TestHubSpotService:
    """Test HubSpot service business logic."""

    @pytest.mark.asyncio
    async def test_hubspot_service_initialization(self):
        """Test HubSpot service initialization."""
        tenant_id = uuid.uuid4()
        integration_id = uuid.uuid4()
        
        service = HubSpotService(tenant_id, integration_id)
        
        assert service.tenant_id == tenant_id
        assert service.integration_id == integration_id
        assert service._client is None

    @pytest.mark.asyncio
    async def test_transform_ticket_to_issue(self):
        """Test HubSpot ticket transformation."""
        tenant_id = uuid.uuid4()
        integration_id = uuid.uuid4()
        service = HubSpotService(tenant_id, integration_id)
        
        # Sample HubSpot ticket
        ticket = {
            "id": "12345",
            "properties": {
                "subject": "Test Ticket",
                "content": "This is a test ticket",
                "hs_ticket_priority": "high",
                "hs_pipeline_stage": "open",
                "hs_ticket_category": "bug"
            }
        }
        
        result = service._transform_ticket_to_issue(ticket)
        
        assert result["tenant_id"] == tenant_id
        assert result["title"] == "Test Ticket"
        assert result["description"] == "This is a test ticket"
        assert result["source"] == "hubspot"
        assert result["severity"] == 4  # "high" priority
        assert result["status"] == "open"
        assert result["type"] == "bug"

    def test_calculate_severity(self):
        """Test severity calculation from HubSpot properties."""
        tenant_id = uuid.uuid4()
        integration_id = uuid.uuid4()
        service = HubSpotService(tenant_id, integration_id)
        
        # Test different priority levels
        assert service._calculate_severity({"hs_ticket_priority": "urgent"}) == 5
        assert service._calculate_severity({"hs_ticket_priority": "high"}) == 4
        assert service._calculate_severity({"hs_ticket_priority": "medium"}) == 3
        assert service._calculate_severity({"hs_ticket_priority": "low"}) == 2
        assert service._calculate_severity({"hs_ticket_priority": ""}) == 1
        assert service._calculate_severity({}) == 1

    def test_extract_ticket_ids_from_webhook(self):
        """Test webhook ticket ID extraction."""
        tenant_id = uuid.uuid4()
        integration_id = uuid.uuid4()
        service = HubSpotService(tenant_id, integration_id)
        
        # Test ticket property change webhook
        webhook_data = {
            "subscriptionType": "ticket.propertyChange",
            "objectId": "12345"
        }
        
        result = service._extract_ticket_ids_from_webhook(webhook_data)
        assert result == ["12345"]
        
        # Test unknown webhook type
        unknown_webhook = {
            "subscriptionType": "unknown.type",
            "objectId": "12345"
        }
        
        result = service._extract_ticket_ids_from_webhook(unknown_webhook)
        assert result == []


class TestSchedulerService:
    """Test scheduler service business logic."""

    def test_scheduler_initialization(self):
        """Test scheduler service initialization."""
        scheduler = SchedulerService()
        
        assert scheduler.running is False
        assert len(scheduler.sync_tasks) == 0
        assert "hubspot" in scheduler.sync_intervals
        assert "jira" in scheduler.sync_intervals
        assert "default" in scheduler.sync_intervals

    @pytest.mark.asyncio
    async def test_scheduler_start_stop(self):
        """Test scheduler start and stop operations."""
        scheduler = SchedulerService()
        
        # Start scheduler
        await scheduler.start()
        assert scheduler.running is True
        
        # Stop scheduler
        await scheduler.stop()
        assert scheduler.running is False

    @pytest.mark.asyncio
    async def test_get_sync_status(self, db_session: AsyncSession):
        """Test getting sync status."""
        scheduler = SchedulerService()
        
        # Create sample integration
        integration = TenantIntegration(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            integration_type="hubspot",
            is_active=True,
            config={"access_token": "test"},
            last_sync_status="success"
        )
        
        db_session.add(integration)
        await db_session.commit()
        
        result = await scheduler.get_sync_status()
        
        assert "running_tasks" in result
        assert "integrations" in result
        assert len(result["integrations"]) >= 1

    @pytest.mark.asyncio
    async def test_trigger_manual_sync(self, db_session: AsyncSession):
        """Test manual sync triggering."""
        scheduler = SchedulerService()
        tenant_id = uuid.uuid4()
        
        # Create sample integration
        integration = TenantIntegration(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            integration_type="hubspot",
            is_active=True,
            config={"access_token": "test"}
        )
        
        db_session.add(integration)
        await db_session.commit()
        
        result = await scheduler.trigger_manual_sync(
            tenant_id=tenant_id,
            integration_type="hubspot",
            sync_type="incremental"
        )
        
        assert "success" in result
        assert "integration_id" in result
        assert "sync_type" in result 