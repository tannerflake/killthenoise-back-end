from __future__ import annotations

import os
import uuid
from typing import AsyncGenerator
from unittest.mock import patch

import pytest
import pytest_asyncio
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant_integration import TenantIntegration
from app.services.hubspot_service import HubSpotService, create_hubspot_service

# Load environment variables
load_dotenv()


@pytest_asyncio.fixture
async def hubspot_credentials() -> dict:
    """Get HubSpot credentials from environment variables."""
    access_token = os.getenv("HUBSPOT_ACCESS_TOKEN")
    if not access_token:
        pytest.skip("HUBSPOT_ACCESS_TOKEN not found in environment variables")
    
    return {
        "access_token": access_token,
        "domain": os.getenv("HUBSPOT_DOMAIN", "api.hubapi.com"),
    }


@pytest_asyncio.fixture
async def test_tenant_integration(
    db_session: AsyncSession, hubspot_credentials: dict
) -> TenantIntegration:
    """Create a test tenant integration with HubSpot credentials."""
    tenant_id = uuid.uuid4()
    integration_id = uuid.uuid4()
    
    integration = TenantIntegration(
        id=integration_id,
        tenant_id=tenant_id,
        integration_type="hubspot",
        is_active=True,
        config=hubspot_credentials,
        webhook_url="https://test.com/webhooks/hubspot",
        webhook_secret="test_secret",
    )
    
    db_session.add(integration)
    await db_session.commit()
    await db_session.refresh(integration)
    
    return integration


class TestHubSpotIntegration:
    """Test HubSpot integration with real credentials."""

    @pytest.mark.asyncio
    async def test_hubspot_connection_status(
        self, db_session: AsyncSession, test_tenant_integration: TenantIntegration
    ):
        """Test that HubSpot connection is working with real credentials."""
        service = create_hubspot_service(
            test_tenant_integration.tenant_id, test_tenant_integration.id
        )
        
        # Test connection status
        is_connected = await service.status()
        assert isinstance(is_connected, bool)
        
        if not is_connected:
            pytest.skip("HubSpot connection failed - check credentials")

    @pytest.mark.asyncio
    async def test_fetch_tickets_from_hubspot(
        self, db_session: AsyncSession, test_tenant_integration: TenantIntegration
    ):
        """Test fetching tickets from HubSpot with real credentials."""
        service = create_hubspot_service(
            test_tenant_integration.tenant_id, test_tenant_integration.id
        )
        
        # First check if we can connect
        is_connected = await service.status()
        if not is_connected:
            pytest.skip("HubSpot connection failed - check credentials")
        
        # Fetch tickets using the private method
        tickets = await service._fetch_tickets()
        
        # Verify we got a list of tickets
        assert isinstance(tickets, list)
        
        # If we have tickets, verify their structure
        if tickets:
            ticket = tickets[0]
            assert "id" in ticket
            assert "properties" in ticket
            
            # Check for expected properties
            props = ticket.get("properties", {})
            assert isinstance(props, dict)
            
            # Log some basic info about the tickets
            print(f"\nFound {len(tickets)} tickets in HubSpot")
            if tickets:
                print(f"Sample ticket ID: {tickets[0]['id']}")
                print(f"Sample ticket subject: {tickets[0].get('properties', {}).get('subject', 'No subject')}")

    @pytest.mark.asyncio
    async def test_transform_ticket_to_issue(
        self, db_session: AsyncSession, test_tenant_integration: TenantIntegration
    ):
        """Test ticket transformation to internal issue format."""
        service = create_hubspot_service(
            test_tenant_integration.tenant_id, test_tenant_integration.id
        )
        
        # Create a sample ticket structure
        sample_ticket = {
            "id": "12345",
            "properties": {
                "subject": "Test Ticket",
                "content": "This is a test ticket content",
                "hs_pipeline_stage": "open",
                "hs_ticket_priority": "medium",
                "hs_ticket_category": "bug",
                "hs_createdate": "1640995200000",  # 2022-01-01
                "hs_lastmodifieddate": "1640995200000",
            }
        }
        
        # Transform the ticket
        issue_dict = service._transform_ticket_to_issue(sample_ticket)
        
        # Verify the transformation
        assert "id" in issue_dict
        assert issue_dict["tenant_id"] == test_tenant_integration.tenant_id
        assert issue_dict["hubspot_ticket_id"] == "12345"
        assert issue_dict["title"] == "Test Ticket"
        assert issue_dict["description"] == "This is a test ticket content"
        assert issue_dict["source"] == "hubspot"
        assert issue_dict["status"] == "open"
        assert issue_dict["type"] == "bug"
        assert issue_dict["tags"] == "medium"
        assert issue_dict["severity"] is not None

    @pytest.mark.asyncio
    async def test_full_sync_with_real_credentials(
        self, db_session: AsyncSession, test_tenant_integration: TenantIntegration
    ):
        """Test full sync with real HubSpot credentials."""
        service = create_hubspot_service(
            test_tenant_integration.tenant_id, test_tenant_integration.id
        )
        
        # Check connection first
        is_connected = await service.status()
        if not is_connected:
            pytest.skip("HubSpot connection failed - check credentials")
        
        # Perform full sync
        result = await service.sync_full()
        
        # Verify sync result structure
        assert isinstance(result, dict)
        assert "success" in result
        assert "processed" in result
        assert "updated" in result
        assert "duration_seconds" in result
        
        # Log sync results
        print(f"\nSync Results:")
        print(f"Success: {result['success']}")
        print(f"Processed: {result['processed']}")
        print(f"Updated: {result['updated']}")
        print(f"Duration: {result['duration_seconds']} seconds")
        
        # Verify we have some results
        assert result["success"] is True
        assert result["processed"] >= 0
        assert result["updated"] >= 0
        assert result["duration_seconds"] >= 0

    @pytest.mark.asyncio
    async def test_incremental_sync_with_real_credentials(
        self, db_session: AsyncSession, test_tenant_integration: TenantIntegration
    ):
        """Test incremental sync with real HubSpot credentials."""
        service = create_hubspot_service(
            test_tenant_integration.tenant_id, test_tenant_integration.id
        )
        
        # Check connection first
        is_connected = await service.status()
        if not is_connected:
            pytest.skip("HubSpot connection failed - check credentials")
        
        # Perform incremental sync
        result = await service.sync_incremental()
        
        # Verify sync result structure
        assert isinstance(result, dict)
        assert "success" in result
        assert "processed" in result
        assert "updated" in result
        assert "duration_seconds" in result
        
        # Log sync results
        print(f"\nIncremental Sync Results:")
        print(f"Success: {result['success']}")
        print(f"Processed: {result['processed']}")
        print(f"Updated: {result['updated']}")
        print(f"Duration: {result['duration_seconds']} seconds")
        
        # Verify we have some results
        assert result["success"] is True
        assert result["processed"] >= 0
        assert result["updated"] >= 0
        assert result["duration_seconds"] >= 0

    @pytest.mark.asyncio
    async def test_calculate_severity_and_frequency(
        self, db_session: AsyncSession, test_tenant_integration: TenantIntegration
    ):
        """Test severity and frequency calculation methods."""
        service = create_hubspot_service(
            test_tenant_integration.tenant_id, test_tenant_integration.id
        )
        
        # Test severity calculation
        test_cases = [
            ({"hs_ticket_priority": "urgent"}, 5),
            ({"hs_ticket_priority": "high"}, 4),
            ({"hs_ticket_priority": "medium"}, 3),
            ({"hs_ticket_priority": "low"}, 2),
            ({"hs_ticket_priority": ""}, 1),
            ({}, 1),
        ]
        
        for props, expected_severity in test_cases:
            severity = service._calculate_severity(props)
            assert severity == expected_severity
        
        # Test frequency calculation (should return None for now)
        frequency = service._calculate_frequency({})
        assert frequency is None

    @pytest.mark.asyncio
    async def test_error_handling_with_invalid_credentials(
        self, db_session: AsyncSession
    ):
        """Test error handling with invalid credentials."""
        # Create integration with invalid credentials
        tenant_id = uuid.uuid4()
        integration_id = uuid.uuid4()
        
        integration = TenantIntegration(
            id=integration_id,
            tenant_id=tenant_id,
            integration_type="hubspot",
            is_active=True,
            config={"access_token": "invalid_token"},
        )
        
        db_session.add(integration)
        await db_session.commit()
        
        service = create_hubspot_service(tenant_id, integration_id)
        
        # Test status with invalid credentials
        is_connected = await service.status()
        assert is_connected is False
        
        # Test sync with invalid credentials should raise an error
        with pytest.raises(Exception):
            await service.sync_full()


class TestHubSpotServiceConfiguration:
    """Test HubSpot service configuration and setup."""

    @pytest.mark.asyncio
    async def test_service_initialization(
        self, db_session: AsyncSession, test_tenant_integration: TenantIntegration
    ):
        """Test HubSpot service initialization."""
        service = create_hubspot_service(
            test_tenant_integration.tenant_id, test_tenant_integration.id
        )
        
        assert service.tenant_id == test_tenant_integration.tenant_id
        assert service.integration_id == test_tenant_integration.id
        assert service._client is None  # Client should be None until first use

    @pytest.mark.asyncio
    async def test_get_integration_config(
        self, db_session: AsyncSession, test_tenant_integration: TenantIntegration
    ):
        """Test getting integration configuration."""
        service = create_hubspot_service(
            test_tenant_integration.tenant_id, test_tenant_integration.id
        )
        
        config = await service._get_integration_config(db_session)
        
        assert isinstance(config, dict)
        assert "access_token" in config
        assert config["access_token"] == test_tenant_integration.config["access_token"]

    @pytest.mark.asyncio
    async def test_get_client_creation(
        self, db_session: AsyncSession, test_tenant_integration: TenantIntegration
    ):
        """Test HTTP client creation."""
        service = create_hubspot_service(
            test_tenant_integration.tenant_id, test_tenant_integration.id
        )
        
        client = await service._get_client(db_session)
        
        assert client is not None
        assert hasattr(client, "base_url")
        assert hasattr(client, "headers")
        assert "Authorization" in client.headers


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "-s"]) 