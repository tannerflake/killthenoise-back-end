#!/usr/bin/env python3
"""Seed the database with realistic demo data for KillTheNoise."""

import asyncio
import os
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models.team import Team
from app.models.tenant_settings import TenantSettings
from app.models.raw_report import RawReport
from app.models.ai_issue_group import AIIssueGroup
from app.models.ai_issue_group_report import AIIssueGroupReport
from app.models.tenant_integration import TenantIntegration


# Demo data
DEMO_TENANT_ID = "550e8400-e29b-41d4-a716-446655440000"

# Demo teams
DEMO_TEAMS = [
    {
        "name": "Frontend Team",
        "description": "Handles all frontend-related issues and user interface problems",
        "assignment_criteria": "frontend, ui, ux, react, javascript, css, html",
        "is_default_team": False,
        "display_order": "1"
    },
    {
        "name": "Backend Team", 
        "description": "Manages server-side issues, APIs, and database problems",
        "assignment_criteria": "backend, api, server, database, python, fastapi, sql",
        "is_default_team": False,
        "display_order": "2"
    },
    {
        "name": "DevOps Team",
        "description": "Handles infrastructure, deployment, and monitoring issues",
        "assignment_criteria": "devops, infrastructure, deployment, monitoring, docker, kubernetes",
        "is_default_team": False,
        "display_order": "3"
    },
    {
        "name": "General Issues",
        "description": "Default team for unassigned issues",
        "assignment_criteria": "general, unassigned, other",
        "is_default_team": True,
        "display_order": "99"
    }
]

# Demo raw reports (individual issues)
DEMO_RAW_REPORTS = [
    # Jira Issues
    {
        "source": "jira",
        "external_id": "PROJ-1234",
        "url": "https://company.atlassian.net/browse/PROJ-1234",
        "title": "Login button not responding on mobile devices",
        "body": "Users are reporting that the login button becomes unresponsive on mobile devices after the latest update. This affects both iOS and Android users.",
        "signature": "login_button_mobile_unresponsive",
        "created_at": datetime.now() - timedelta(days=2)
    },
    {
        "source": "jira", 
        "external_id": "PROJ-1235",
        "url": "https://company.atlassian.net/browse/PROJ-1235",
        "title": "Database connection timeout errors",
        "body": "Getting frequent database connection timeout errors in production. This is causing 500 errors for users.",
        "signature": "database_connection_timeout",
        "created_at": datetime.now() - timedelta(days=1)
    },
    {
        "source": "jira",
        "external_id": "PROJ-1236", 
        "url": "https://company.atlassian.net/browse/PROJ-1236",
        "title": "API rate limiting too aggressive",
        "body": "The API rate limiting is blocking legitimate users. Need to adjust the thresholds.",
        "signature": "api_rate_limiting_aggressive",
        "created_at": datetime.now() - timedelta(hours=6)
    },
    
    # HubSpot Issues
    {
        "source": "hubspot",
        "external_id": "HS-789",
        "url": "https://app.hubspot.com/contacts/123456789/deal/789",
        "title": "Customer unable to access premium features",
        "body": "Customer reports they cannot access premium features despite having an active subscription. Billing shows they are current.",
        "signature": "premium_features_access_denied",
        "created_at": datetime.now() - timedelta(days=3)
    },
    {
        "source": "hubspot",
        "external_id": "HS-790",
        "url": "https://app.hubspot.com/contacts/123456789/deal/790", 
        "title": "Email notifications not being sent",
        "body": "Customer is not receiving email notifications for important updates. Checked spam folder and email settings.",
        "signature": "email_notifications_not_sent",
        "created_at": datetime.now() - timedelta(days=1)
    },
    {
        "source": "hubspot",
        "external_id": "HS-791",
        "url": "https://app.hubspot.com/contacts/123456789/deal/791",
        "title": "Dashboard loading very slowly",
        "body": "Customer reports that the dashboard takes over 30 seconds to load, making it unusable.",
        "signature": "dashboard_slow_loading",
        "created_at": datetime.now() - timedelta(hours=12)
    },
    
    # Slack Issues
    {
        "source": "slack",
        "external_id": "SL-456",
        "url": "https://company.slack.com/archives/C1234567890/p1234567890123456",
        "title": "Integration with Salesforce not working",
        "body": "The Salesforce integration has stopped syncing data. Last successful sync was 2 days ago.",
        "signature": "salesforce_integration_broken",
        "created_at": datetime.now() - timedelta(days=2)
    },
    {
        "source": "slack",
        "external_id": "SL-457", 
        "url": "https://company.slack.com/archives/C1234567890/p1234567890123457",
        "title": "File upload failing for large files",
        "body": "Users cannot upload files larger than 10MB. Getting error message 'File too large' even for files under the limit.",
        "signature": "file_upload_large_files_failing",
        "created_at": datetime.now() - timedelta(days=1)
    },
    {
        "source": "slack",
        "external_id": "SL-458",
        "url": "https://company.slack.com/archives/C1234567890/p1234567890123458", 
        "title": "Search functionality returning no results",
        "body": "The search feature is not returning any results, even for terms that should definitely match existing content.",
        "signature": "search_functionality_broken",
        "created_at": datetime.now() - timedelta(hours=8)
    },
    
    # Additional issues for grouping
    {
        "source": "jira",
        "external_id": "PROJ-1237",
        "url": "https://company.atlassian.net/browse/PROJ-1237",
        "title": "Login button not working on tablet devices",
        "body": "Similar to mobile issue, login button is also not responding on tablet devices.",
        "signature": "login_button_mobile_unresponsive",
        "created_at": datetime.now() - timedelta(days=1)
    },
    {
        "source": "hubspot", 
        "external_id": "HS-792",
        "url": "https://app.hubspot.com/contacts/123456789/deal/792",
        "title": "Login button unresponsive on mobile app",
        "body": "Customer reports login button not working on mobile app version 2.1.3.",
        "signature": "login_button_mobile_unresponsive",
        "created_at": datetime.now() - timedelta(hours=18)
    },
    {
        "source": "slack",
        "external_id": "SL-459",
        "url": "https://company.slack.com/archives/C1234567890/p1234567890123459",
        "title": "Mobile login button issue",
        "body": "Multiple users reporting login button not responding on mobile devices.",
        "signature": "login_button_mobile_unresponsive", 
        "created_at": datetime.now() - timedelta(hours=4)
    },
    {
        "source": "jira",
        "external_id": "PROJ-1238",
        "url": "https://company.atlassian.net/browse/PROJ-1238",
        "title": "Database connection pool exhausted",
        "body": "Database connection pool is getting exhausted, causing connection timeouts.",
        "signature": "database_connection_timeout",
        "created_at": datetime.now() - timedelta(hours=10)
    },
    {
        "source": "hubspot",
        "external_id": "HS-793", 
        "url": "https://app.hubspot.com/contacts/123456789/deal/793",
        "title": "Database timeout when loading customer data",
        "body": "Getting database timeout errors when trying to load customer data in the dashboard.",
        "signature": "database_connection_timeout",
        "created_at": datetime.now() - timedelta(hours=2)
    }
]

# Demo AI Issue Groups (grouped issues)
DEMO_AI_GROUPS = [
    {
        "title": "Login Button Not Responding on Mobile Devices",
        "summary": "sig:login_button_mobile_unresponsive|Multiple reports of login button becoming unresponsive on mobile and tablet devices after recent updates",
        "severity": 85,
        "tags": "mobile,login,ui,critical",
        "status": "open",
        "frequency": 4,
        "sources": [
            {"source": "jira", "count": 2},
            {"source": "hubspot", "count": 1}, 
            {"source": "slack", "count": 1}
        ],
        "confidence": 0.95,
        "team_id": 0  # Frontend Team
    },
    {
        "title": "Database Connection Timeout Issues",
        "summary": "sig:database_connection_timeout|Frequent database connection timeouts causing 500 errors and service degradation",
        "severity": 92,
        "tags": "database,performance,critical,backend",
        "status": "open", 
        "frequency": 3,
        "sources": [
            {"source": "jira", "count": 2},
            {"source": "hubspot", "count": 1}
        ],
        "confidence": 0.88,
        "team_id": 1  # Backend Team
    },
    {
        "title": "API Rate Limiting Too Aggressive",
        "summary": "sig:api_rate_limiting_aggressive|API rate limiting is blocking legitimate users and needs threshold adjustment",
        "severity": 65,
        "tags": "api,rate-limiting,backend",
        "status": "open",
        "frequency": 1,
        "sources": [
            {"source": "jira", "count": 1}
        ],
        "confidence": 0.75,
        "team_id": 1  # Backend Team
    },
    {
        "title": "Customer Premium Features Access Denied",
        "summary": "sig:premium_features_access_denied|Customer cannot access premium features despite active subscription",
        "severity": 78,
        "tags": "billing,premium,access,frontend",
        "status": "open",
        "frequency": 1,
        "sources": [
            {"source": "hubspot", "count": 1}
        ],
        "confidence": 0.82,
        "team_id": 0  # Frontend Team
    },
    {
        "title": "Email Notifications Not Being Sent",
        "summary": "sig:email_notifications_not_sent|Customer not receiving email notifications for important updates",
        "severity": 55,
        "tags": "email,notifications,backend",
        "status": "open",
        "frequency": 1,
        "sources": [
            {"source": "hubspot", "count": 1}
        ],
        "confidence": 0.70,
        "team_id": 2  # DevOps Team
    },
    {
        "title": "Dashboard Loading Performance Issues",
        "summary": "sig:dashboard_slow_loading|Dashboard takes over 30 seconds to load, making it unusable",
        "severity": 72,
        "tags": "performance,dashboard,frontend",
        "status": "open",
        "frequency": 1,
        "sources": [
            {"source": "hubspot", "count": 1}
        ],
        "confidence": 0.85,
        "team_id": 0  # Frontend Team
    },
    {
        "title": "Salesforce Integration Sync Failure",
        "summary": "sig:salesforce_integration_broken|Salesforce integration has stopped syncing data, last successful sync 2 days ago",
        "severity": 68,
        "tags": "integration,salesforce,backend",
        "status": "open",
        "frequency": 1,
        "sources": [
            {"source": "slack", "count": 1}
        ],
        "confidence": 0.80,
        "team_id": 2  # DevOps Team
    },
    {
        "title": "File Upload Failing for Large Files",
        "summary": "sig:file_upload_large_files_failing|Users cannot upload files larger than 10MB, getting false 'File too large' errors",
        "severity": 60,
        "tags": "file-upload,storage,frontend",
        "status": "open",
        "frequency": 1,
        "sources": [
            {"source": "slack", "count": 1}
        ],
        "confidence": 0.75,
        "team_id": 0  # Frontend Team
    },
    {
        "title": "Search Functionality Not Returning Results",
        "summary": "sig:search_functionality_broken|Search feature not returning any results, even for terms that should match",
        "severity": 58,
        "tags": "search,functionality,backend",
        "status": "open",
        "frequency": 1,
        "sources": [
            {"source": "slack", "count": 1}
        ],
        "confidence": 0.78,
        "team_id": 1  # Backend Team
    }
]


async def create_demo_teams(session: AsyncSession) -> List[Team]:
    """Create demo teams."""
    print("Creating demo teams...")
    teams = []
    
    for team_data in DEMO_TEAMS:
        team = Team(
            id=uuid.uuid4(),
            tenant_id=uuid.UUID(DEMO_TENANT_ID),
            name=team_data["name"],
            description=team_data["description"],
            assignment_criteria=team_data["assignment_criteria"],
            is_default_team=team_data["is_default_team"],
            display_order=team_data["display_order"]
        )
        session.add(team)
        teams.append(team)
    
    await session.commit()
    print(f"✅ Created {len(teams)} demo teams")
    return teams


async def create_tenant_settings(session: AsyncSession):
    """Create tenant settings."""
    print("Creating tenant settings...")
    
    settings = TenantSettings(
        tenant_id=uuid.UUID(DEMO_TENANT_ID),
        grouping_instructions="Group similar issues by signature and source. Focus on user-facing problems and technical issues.",
        type_classification_instructions="Classify as bug, feature, or enhancement based on issue description and impact.",
        severity_calculation_instructions="Calculate severity based on user impact, frequency, and business criticality. Range 0-100."
    )
    session.add(settings)
    await session.commit()
    print("✅ Created tenant settings")


async def create_demo_integrations(session: AsyncSession):
    """Create demo integrations."""
    print("Creating demo integrations...")
    
    integrations = [
        {
            "integration_type": "jira",
            "is_active": True,
            "config": {
                "base_url": "https://company.atlassian.net",
                "project_key": "PROJ"
            }
        },
        {
            "integration_type": "hubspot", 
            "is_active": True,
            "config": {
                "portal_id": "123456789",
                "api_key": "demo_key"
            }
        },
        {
            "integration_type": "slack",
            "is_active": True,
            "config": {
                "workspace_id": "T1234567890",
                "channel_id": "C1234567890"
            }
        }
    ]
    
    for integration_data in integrations:
        integration = TenantIntegration(
            id=uuid.uuid4(),
            tenant_id=uuid.UUID(DEMO_TENANT_ID),
            integration_type=integration_data["integration_type"],
            is_active=integration_data["is_active"],
            config=integration_data["config"]
        )
        session.add(integration)
    
    await session.commit()
    print("✅ Created demo integrations")


async def create_demo_raw_reports(session: AsyncSession) -> List[RawReport]:
    """Create demo raw reports."""
    print("Creating demo raw reports...")
    
    reports = []
    for report_data in DEMO_RAW_REPORTS:
        report = RawReport(
            id=uuid.uuid4(),
            tenant_id=uuid.UUID(DEMO_TENANT_ID),
            source=report_data["source"],
            external_id=report_data["external_id"],
            url=report_data["url"],
            title=report_data["title"],
            body=report_data["body"],
            signature=report_data["signature"],
            created_at=report_data["created_at"]
        )
        session.add(report)
        reports.append(report)
    
    await session.commit()
    print(f"✅ Created {len(reports)} demo raw reports")
    return reports


async def create_demo_ai_groups(session: AsyncSession, teams: List[Team], reports: List[RawReport]) -> List[AIIssueGroup]:
    """Create demo AI issue groups."""
    print("Creating demo AI issue groups...")
    
    # Create a mapping of signatures to reports
    signature_to_reports = {}
    for report in reports:
        if report.signature not in signature_to_reports:
            signature_to_reports[report.signature] = []
        signature_to_reports[report.signature].append(report)
    
    ai_groups = []
    for group_data in DEMO_AI_GROUPS:
        # Extract signature from summary
        signature = group_data["summary"].split("|")[0].replace("sig:", "")
        
        # Get team
        team = teams[group_data["team_id"]] if group_data["team_id"] < len(teams) else teams[-1]
        
        ai_group = AIIssueGroup(
            id=uuid.uuid4(),
            tenant_id=uuid.UUID(DEMO_TENANT_ID),
            title=group_data["title"],
            summary=group_data["summary"],
            severity=group_data["severity"],
            tags=group_data["tags"],
            status=group_data["status"],
            frequency=group_data["frequency"],
            sources=group_data["sources"],
            confidence=group_data["confidence"],
            team_id=team.id
        )
        session.add(ai_group)
        ai_groups.append(ai_group)
    
    await session.commit()
    print(f"✅ Created {len(ai_groups)} demo AI issue groups")
    return ai_groups


async def create_group_report_links(session: AsyncSession, ai_groups: List[AIIssueGroup], reports: List[RawReport]):
    """Create links between AI groups and their reports."""
    print("Creating group-report links...")
    
    # Create a mapping of signatures to reports
    signature_to_reports = {}
    for report in reports:
        if report.signature not in signature_to_reports:
            signature_to_reports[report.signature] = []
        signature_to_reports[report.signature].append(report)
    
    links_created = 0
    for ai_group in ai_groups:
        # Extract signature from summary
        signature = ai_group.summary.split("|")[0].replace("sig:", "")
        
        if signature in signature_to_reports:
            for report in signature_to_reports[signature]:
                link = AIIssueGroupReport(
                    group_id=ai_group.id,
                    report_id=report.id
                )
                session.add(link)
                links_created += 1
    
    await session.commit()
    print(f"✅ Created {links_created} group-report links")


async def main():
    """Main function to seed the database."""
    print("🌱 Seeding database with demo data...")
    
    # Set up database connection
    database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./killthenoise.db")
    engine = create_async_engine(database_url, echo=False)
    AsyncSessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    
    try:
        async with AsyncSessionLocal() as session:
            # Create teams first
            teams = await create_demo_teams(session)
            
            # Create tenant settings
            await create_tenant_settings(session)
            
            # Create integrations
            await create_demo_integrations(session)
            
            # Create raw reports
            reports = await create_demo_raw_reports(session)
            
            # Create AI groups
            ai_groups = await create_demo_ai_groups(session, teams, reports)
            
            # Create group-report links
            await create_group_report_links(session, ai_groups, reports)
            
        print("\n🎉 Demo data seeding completed successfully!")
        print(f"📊 Created:")
        print(f"   - {len(teams)} teams")
        print(f"   - {len(reports)} raw reports")
        print(f"   - {len(ai_groups)} AI issue groups")
        print(f"   - Multiple integrations and settings")
        
    except Exception as e:
        print(f"❌ Error seeding database: {e}")
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
