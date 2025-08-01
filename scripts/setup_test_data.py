#!/usr/bin/env python3
"""Setup test data and environment for KillTheNoise backend testing."""

import os
import uuid
import asyncio
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db import get_db
from app.models.issue import Issue
from app.models.tenant_integration import TenantIntegration
from app.models.sync_event import SyncEvent


async def setup_test_data():
    """Create test data for the application."""
    print("🔧 Setting up test data...")
    
    # Create test tenant
    tenant_id = uuid.uuid4()
    integration_id = uuid.uuid4()
    
    async for session in get_db():
        # Create tenant integration
        integration = TenantIntegration(
            id=integration_id,
            tenant_id=tenant_id,
            integration_type="hubspot",
            is_active=True,
            config={
                "access_token": "test_hubspot_token",
                "domain": "test.hubapi.com",
                "client_id": "c4f6d977-f797-4c43-9e9d-9bc867ea01ac",
                "client_secret": "1ba8cccc-757d-44e9-81c7-21aff3b91e07"
            },
            last_synced_at=datetime.utcnow() - timedelta(hours=1),
            last_sync_status="success",
            webhook_url="http://localhost:8000/api/webhooks/hubspot",
            webhook_secret="test_webhook_secret"
        )
        session.add(integration)
        
        # Create sample issues
        issues = [
            Issue(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                title="Critical Bug in Payment System",
                description="Users are unable to complete payments",
                source="hubspot",
                severity=5,
                frequency=15,
                status="open",
                type="bug",
                tags="critical,payment,urgent",
                hubspot_ticket_id="12345",
                created_at=datetime.utcnow() - timedelta(days=2)
            ),
            Issue(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                title="Feature Request: Dark Mode",
                description="Users want a dark mode option",
                source="hubspot",
                severity=3,
                frequency=8,
                status="in_progress",
                type="feature",
                tags="ui,feature,enhancement",
                hubspot_ticket_id="12346",
                created_at=datetime.utcnow() - timedelta(days=5)
            ),
            Issue(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                title="Performance Issue: Slow Loading",
                description="Dashboard takes too long to load",
                source="jira",
                severity=4,
                frequency=12,
                status="resolved",
                type="performance",
                tags="performance,optimization",
                jira_issue_key="KTN-123",
                created_at=datetime.utcnow() - timedelta(days=1)
            ),
            Issue(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                title="Security Vulnerability Found",
                description="Potential SQL injection in login form",
                source="hubspot",
                severity=5,
                frequency=3,
                status="open",
                type="security",
                tags="security,critical,vulnerability",
                hubspot_ticket_id="12347",
                created_at=datetime.utcnow() - timedelta(hours=6)
            ),
            Issue(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                title="User Feedback: Better Search",
                description="Search functionality needs improvement",
                source="jira",
                severity=2,
                frequency=5,
                status="open",
                type="enhancement",
                tags="search,ui,feedback",
                jira_issue_key="KTN-124",
                created_at=datetime.utcnow() - timedelta(days=3)
            )
        ]
        
        for issue in issues:
            session.add(issue)
        
        # Create sync events
        sync_events = [
            SyncEvent(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                integration_id=integration_id,
                event_type="incremental",
                status="success",
                items_processed=25,
                items_created=5,
                items_updated=15,
                items_deleted=5,
                duration_seconds=30,
                started_at=datetime.utcnow() - timedelta(hours=1),
                completed_at=datetime.utcnow() - timedelta(hours=1) + timedelta(seconds=30)
            ),
            SyncEvent(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                integration_id=integration_id,
                event_type="webhook",
                status="success",
                items_processed=3,
                items_created=1,
                items_updated=2,
                items_deleted=0,
                duration_seconds=5,
                started_at=datetime.utcnow() - timedelta(minutes=30),
                completed_at=datetime.utcnow() - timedelta(minutes=30) + timedelta(seconds=5)
            )
        ]
        
        for event in sync_events:
            session.add(event)
        
        await session.commit()
        
        print(f"✅ Created test data:")
        print(f"   - Tenant ID: {tenant_id}")
        print(f"   - Integration ID: {integration_id}")
        print(f"   - Issues: {len(issues)}")
        print(f"   - Sync Events: {len(sync_events)}")
        
        return str(tenant_id), str(integration_id)


def setup_environment():
    """Set up environment variables."""
    env_vars = {
        "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
        "HUBSPOT_CLIENT_ID": "c4f6d977-f797-4c43-9e9d-9bc867ea01ac",
        "HUBSPOT_CLIENT_SECRET": "1ba8cccc-757d-44e9-81c7-21aff3b91e07",
        "HUBSPOT_REDIRECT_URI": "http://localhost:5001/api/hubspot/callback",
        "ENVIRONMENT": "development"
    }
    
    for key, value in env_vars.items():
        os.environ[key] = value
    
    print("✅ Environment variables set")


async def main():
    """Main setup function."""
    print("🚀 Setting up KillTheNoise test environment...")
    
    # Set environment variables
    setup_environment()
    
    # Create test data
    tenant_id, integration_id = await setup_test_data()
    
    print("\n🎉 Setup complete!")
    print(f"📊 Test Tenant ID: {tenant_id}")
    print(f"🔗 Test Integration ID: {integration_id}")
    print("\n🌐 You can now test the API endpoints with this data.")
    print("📖 API Documentation: http://localhost:8000/docs")


if __name__ == "__main__":
    asyncio.run(main()) 