from __future__ import annotations

import datetime as dt
import uuid
from typing import Any, Dict

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.issue import Issue
from app.models.sync_event import SyncEvent
from app.models.tenant_integration import TenantIntegration


class TestIssueModel:
    """Test Issue model functionality."""

    @pytest.mark.asyncio
    async def test_issue_creation(self, db_session: AsyncSession):
        """Test creating an issue."""
        tenant_id = uuid.uuid4()
        issue = Issue(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            title="Test Issue",
            description="This is a test issue",
            source="hubspot",
            severity=3,
            status="open",
            type="bug",
            tags="medium",
            hubspot_ticket_id="12345",
        )

        db_session.add(issue)
        await db_session.commit()

        # Verify the issue was created
        assert issue.id is not None
        assert issue.tenant_id == tenant_id
        assert issue.title == "Test Issue"
        assert issue.source == "hubspot"
        assert issue.severity == 3
        assert issue.created_at is not None

    @pytest.mark.asyncio
    async def test_issue_update(self, db_session: AsyncSession):
        """Test updating an issue."""
        tenant_id = uuid.uuid4()
        issue = Issue(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            title="Original Title",
            source="hubspot",
            severity=2,
        )

        db_session.add(issue)
        await db_session.commit()

        # Update the issue
        issue.title = "Updated Title"
        issue.severity = 4
        await db_session.commit()

        # Verify the update
        assert issue.title == "Updated Title"
        assert issue.severity == 4
        # Note: updated_at is set by database trigger, not immediately available in session

    @pytest.mark.asyncio
    async def test_issue_tenant_isolation(self, db_session: AsyncSession):
        """Test that issues are properly isolated by tenant."""
        tenant_1 = uuid.uuid4()
        tenant_2 = uuid.uuid4()

        # Create issues for different tenants
        issue_1 = Issue(
            id=uuid.uuid4(),
            tenant_id=tenant_1,
            title="Tenant 1 Issue",
            source="hubspot",
        )

        issue_2 = Issue(
            id=uuid.uuid4(), tenant_id=tenant_2, title="Tenant 2 Issue", source="jira"
        )

        db_session.add_all([issue_1, issue_2])
        await db_session.commit()

        # Verify tenant isolation
        assert issue_1.tenant_id == tenant_1
        assert issue_2.tenant_id == tenant_2
        assert issue_1.tenant_id != issue_2.tenant_id

    @pytest.mark.asyncio
    async def test_issue_severity_validation(self, db_session: AsyncSession):
        """Test issue severity validation."""
        tenant_id = uuid.uuid4()

        # Test valid severities
        for severity in [1, 2, 3, 4, 5]:
            issue = Issue(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                title=f"Issue with severity {severity}",
                source="hubspot",
                severity=severity,
            )
            db_session.add(issue)

        await db_session.commit()

        # Verify all issues were created using ORM
        from sqlalchemy import select
        stmt = select(Issue.severity).where(Issue.tenant_id == tenant_id)
        result = await db_session.execute(stmt)
        severities = [row[0] for row in result.fetchall()]
        assert set(severities) == {1, 2, 3, 4, 5}


class TestTenantIntegrationModel:
    """Test TenantIntegration model functionality."""

    @pytest.mark.asyncio
    async def test_integration_creation(self, db_session: AsyncSession):
        """Test creating a tenant integration."""
        tenant_id = uuid.uuid4()
        integration = TenantIntegration(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            integration_type="hubspot",
            is_active=True,
            config={"access_token": "test_token", "domain": "test.hubapi.com"},
            webhook_url="https://test.com/webhooks/hubspot",
            webhook_secret="test_secret",
        )

        db_session.add(integration)
        await db_session.commit()

        # Verify the integration was created
        assert integration.id is not None
        assert integration.tenant_id == tenant_id
        assert integration.integration_type == "hubspot"
        assert integration.is_active is True
        assert "access_token" in integration.config
        assert integration.webhook_url == "https://test.com/webhooks/hubspot"

    @pytest.mark.asyncio
    async def test_integration_config_storage(self, db_session: AsyncSession):
        """Test that integration config is properly stored and retrieved."""
        tenant_id = uuid.uuid4()
        config = {
            "access_token": "secret_token_123",
            "domain": "company.hubapi.com",
            "api_version": "v3",
            "rate_limit": 100,
        }

        integration = TenantIntegration(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            integration_type="hubspot",
            config=config,
        )

        db_session.add(integration)
        await db_session.commit()

        # Verify config is stored correctly
        assert integration.config == config
        assert integration.config["access_token"] == "secret_token_123"
        assert integration.config["domain"] == "company.hubapi.com"

    @pytest.mark.asyncio
    async def test_integration_sync_tracking(self, db_session: AsyncSession):
        """Test sync tracking functionality."""
        tenant_id = uuid.uuid4()
        integration = TenantIntegration(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            integration_type="hubspot",
            config={"access_token": "test"},
        )

        db_session.add(integration)
        await db_session.commit()

        # Update sync status
        integration.last_synced_at = dt.datetime.utcnow()
        integration.last_sync_status = "success"
        integration.sync_error_message = None
        await db_session.commit()

        # Verify sync tracking
        assert integration.last_synced_at is not None
        assert integration.last_sync_status == "success"
        assert integration.sync_error_message is None

    @pytest.mark.asyncio
    async def test_integration_error_handling(self, db_session: AsyncSession):
        """Test integration error tracking."""
        tenant_id = uuid.uuid4()
        integration = TenantIntegration(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            integration_type="hubspot",
            config={"access_token": "invalid_token"},
        )

        db_session.add(integration)
        await db_session.commit()

        # Simulate sync error
        integration.last_sync_status = "failed"
        integration.sync_error_message = "Invalid access token"
        await db_session.commit()

        # Verify error tracking
        assert integration.last_sync_status == "failed"
        assert integration.sync_error_message == "Invalid access token"


class TestSyncEventModel:
    """Test SyncEvent model functionality."""

    @pytest.mark.asyncio
    async def test_sync_event_creation(self, db_session: AsyncSession):
        """Test creating a sync event."""
        tenant_id = uuid.uuid4()
        integration_id = uuid.uuid4()

        sync_event = SyncEvent(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            integration_id=integration_id,
            event_type="incremental",
            status="success",
            items_processed=10,
            items_created=5,
            items_updated=3,
            items_deleted=2,
            duration_seconds=30,
            source_data={"test": "data"},
        )

        db_session.add(sync_event)
        await db_session.commit()

        # Verify the sync event was created
        assert sync_event.id is not None
        assert sync_event.tenant_id == tenant_id
        assert sync_event.integration_id == integration_id
        assert sync_event.event_type == "incremental"
        assert sync_event.status == "success"
        assert sync_event.items_processed == 10
        assert sync_event.duration_seconds == 30

    @pytest.mark.asyncio
    async def test_sync_event_timing(self, db_session: AsyncSession):
        """Test sync event timing functionality."""
        tenant_id = uuid.uuid4()
        integration_id = uuid.uuid4()

        start_time = dt.datetime.utcnow()

        sync_event = SyncEvent(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            integration_id=integration_id,
            event_type="full",
            status="running",
            started_at=start_time,
        )

        db_session.add(sync_event)
        await db_session.commit()

        # Simulate sync completion
        sync_event.status = "success"
        sync_event.completed_at = dt.datetime.utcnow()
        sync_event.duration_seconds = 45
        await db_session.commit()

        # Verify timing
        assert sync_event.started_at == start_time
        assert sync_event.completed_at is not None
        assert sync_event.duration_seconds == 45
        assert sync_event.status == "success"

    @pytest.mark.asyncio
    async def test_sync_event_error_tracking(self, db_session: AsyncSession):
        """Test sync event error tracking."""
        tenant_id = uuid.uuid4()
        integration_id = uuid.uuid4()

        sync_event = SyncEvent(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            integration_id=integration_id,
            event_type="incremental",
            status="failed",
            error_message="API rate limit exceeded",
            error_details={"error_code": 429, "retry_after": 60},
        )

        db_session.add(sync_event)
        await db_session.commit()

        # Verify error tracking
        assert sync_event.status == "failed"
        assert sync_event.error_message == "API rate limit exceeded"
        assert sync_event.error_details["error_code"] == 429

    @pytest.mark.asyncio
    async def test_sync_event_performance_metrics(self, db_session: AsyncSession):
        """Test sync event performance metrics."""
        tenant_id = uuid.uuid4()
        integration_id = uuid.uuid4()

        sync_event = SyncEvent(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            integration_id=integration_id,
            event_type="webhook",
            status="success",
            items_processed=100,
            items_created=20,
            items_updated=70,
            items_deleted=10,
            duration_seconds=15,
        )

        db_session.add(sync_event)
        await db_session.commit()

        # Verify performance metrics
        assert sync_event.items_processed == 100
        assert sync_event.items_created == 20
        assert sync_event.items_updated == 70
        assert sync_event.items_deleted == 10
        assert sync_event.duration_seconds == 15

        # Calculate efficiency
        efficiency = (
            (sync_event.items_processed / sync_event.duration_seconds)
            if sync_event.duration_seconds > 0
            else 0
        )
        assert efficiency == 100 / 15  # 6.67 items per second
