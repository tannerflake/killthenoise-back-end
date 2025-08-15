#!/usr/bin/env python3
"""
Script to create test issues for the dashboard.
"""

import asyncio
import uuid
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.issue import Issue

# Test tenant ID
TENANT_ID = UUID("550e8400-e29b-41d4-a716-446655440000")

# Test issues data
TEST_ISSUES = [
    {
        "id": uuid.uuid4(),
        "tenant_id": TENANT_ID,
        "title": "High Priority Bug in Login System",
        "description": "Users are experiencing intermittent login failures. The issue appears to be related to session timeout handling.",
        "source": "jira",
        "severity": 5,
        "frequency": 3,
        "status": "open",
        "type": "bug",
        "tags": "authentication,login,high-priority",
        "jira_issue_key": "PROJ-123",
        "ai_enabled": True,
        "ai_sentiment": "frustrated",
        "ai_urgency": 0.9,
        "ai_category": "authentication",
        "ai_tags": "login,security,user-experience",
        "ai_severity_confidence": 0.85,
        "ai_sentiment_confidence": 0.78,
        "ai_category_confidence": 0.92,
        "ai_severity_reasoning": "Critical user-facing issue affecting core functionality",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    },
    {
        "id": uuid.uuid4(),
        "tenant_id": TENANT_ID,
        "title": "Feature Request: Dark Mode Support",
        "description": "Users have requested dark mode support for better accessibility and user experience.",
        "source": "hubspot",
        "severity": 3,
        "frequency": 1,
        "status": "pending",
        "type": "enhancement",
        "tags": "ui,accessibility,feature-request",
        "hubspot_ticket_id": "HS-456",
        "ai_enabled": True,
        "ai_sentiment": "neutral",
        "ai_urgency": 0.4,
        "ai_category": "ui-enhancement",
        "ai_tags": "dark-mode,accessibility,user-experience",
        "ai_severity_confidence": 0.65,
        "ai_sentiment_confidence": 0.72,
        "ai_category_confidence": 0.88,
        "ai_severity_reasoning": "Enhancement request with moderate user impact",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    },
    {
        "id": uuid.uuid4(),
        "tenant_id": TENANT_ID,
        "title": "Performance Issue: Slow Database Queries",
        "description": "Database queries are taking longer than expected, affecting overall application performance.",
        "source": "jira",
        "severity": 4,
        "frequency": 2,
        "status": "in-progress",
        "type": "performance",
        "tags": "database,performance,optimization",
        "jira_issue_key": "PROJ-789",
        "ai_enabled": True,
        "ai_sentiment": "frustrated",
        "ai_urgency": 0.7,
        "ai_category": "performance",
        "ai_tags": "database,optimization,performance",
        "ai_severity_confidence": 0.78,
        "ai_sentiment_confidence": 0.65,
        "ai_category_confidence": 0.85,
        "ai_severity_reasoning": "Performance issue affecting user experience",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    },
    {
        "id": uuid.uuid4(),
        "tenant_id": TENANT_ID,
        "title": "Customer Support: Billing Question",
        "description": "Customer has questions about their billing statement and payment options.",
        "source": "hubspot",
        "severity": 2,
        "frequency": 1,
        "status": "resolved",
        "type": "support",
        "tags": "billing,customer-support",
        "hubspot_ticket_id": "HS-101",
        "ai_enabled": True,
        "ai_sentiment": "neutral",
        "ai_urgency": 0.3,
        "ai_category": "billing",
        "ai_tags": "billing,customer-support,payment",
        "ai_severity_confidence": 0.45,
        "ai_sentiment_confidence": 0.68,
        "ai_category_confidence": 0.75,
        "ai_severity_reasoning": "Standard customer support inquiry",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    },
    {
        "id": uuid.uuid4(),
        "tenant_id": TENANT_ID,
        "title": "Security Vulnerability: SQL Injection Risk",
        "description": "Potential SQL injection vulnerability identified in user input handling.",
        "source": "jira",
        "severity": 5,
        "frequency": 1,
        "status": "open",
        "type": "security",
        "tags": "security,vulnerability,high-priority",
        "jira_issue_key": "PROJ-234",
        "ai_enabled": True,
        "ai_sentiment": "frustrated",
        "ai_urgency": 1.0,
        "ai_category": "security",
        "ai_tags": "security,vulnerability,sql-injection",
        "ai_severity_confidence": 0.95,
        "ai_sentiment_confidence": 0.82,
        "ai_category_confidence": 0.98,
        "ai_severity_reasoning": "Critical security vulnerability requiring immediate attention",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
]

async def create_test_issues():
    """Create test issues in the database."""
    async for session in get_db():
        try:
            # Insert test issues
            for issue_data in TEST_ISSUES:
                stmt = insert(Issue).values(**issue_data)
                await session.execute(stmt)
            
            await session.commit()
            print(f"✅ Successfully created {len(TEST_ISSUES)} test issues")
            
            # Verify the issues were created
            from sqlalchemy import select
            stmt = select(Issue).where(Issue.tenant_id == TENANT_ID)
            result = await session.execute(stmt)
            issues = result.scalars().all()
            print(f"📊 Total issues in database: {len(issues)}")
            
        except Exception as e:
            print(f"❌ Error creating test issues: {e}")
            await session.rollback()
            raise

if __name__ == "__main__":
    asyncio.run(create_test_issues()) 