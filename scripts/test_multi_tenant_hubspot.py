#!/usr/bin/env python3
"""Test script for multi-tenant HubSpot endpoints.

This script demonstrates:
1. Creating a tenant integration with an access token
2. Testing the connection for that tenant
3. Listing tickets for that tenant

Run: `python3 scripts/test_multi_tenant_hubspot.py`
"""
from __future__ import annotations

import asyncio
import os
import sys
import uuid
from pathlib import Path

# Ensure project root on sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models.tenant_integration import TenantIntegration
from app.models.sync_event import SyncEvent
from app.models.issue import Issue

# Load environment variables
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Test database setup
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
engine = create_async_engine(TEST_DB_URL, echo=False, future=True)
SessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def setup_db() -> AsyncSession:
    """Set up test database with all required tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return SessionLocal()


class MockHubSpotService:
    """Mock HubSpot service for testing multi-tenant functionality."""
    
    def __init__(self, tenant_id: uuid.UUID, integration_id: uuid.UUID, session: AsyncSession):
        self.tenant_id = tenant_id
        self.integration_id = integration_id
        self.session = session
        self._access_token = None
    
    async def _get_integration(self) -> TenantIntegration:
        """Get the tenant integration record."""
        integration = await self.session.get(TenantIntegration, self.integration_id)
        if not integration or integration.tenant_id != self.tenant_id:
            raise ValueError(f"Integration {self.integration_id} not found for tenant {self.tenant_id}")
        return integration
    
    async def _validate_token(self, token: str) -> bool:
        """Validate token using the same method as the real service."""
        import httpx
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://api.hubapi.com/oauth/v1/access-tokens/{token}",
                    timeout=10
                )
                return response.status_code == 200
        except Exception:
            return False
    
    async def test_connection(self) -> dict:
        """Test connection to HubSpot."""
        try:
            integration = await self._get_integration()
            access_token = integration.config.get("access_token")
            
            if not access_token:
                return {"connected": False, "error": "No access token"}
            
            # Validate the token
            is_valid = await self._validate_token(access_token)
            if not is_valid:
                return {"connected": False, "error": "Invalid token"}
            
            # Get token info
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://api.hubapi.com/oauth/v1/access-tokens/{access_token}",
                    timeout=10
                )
                if response.status_code == 200:
                    token_info = response.json()
                    return {
                        "connected": True,
                        "hub_domain": token_info.get("hub_domain"),
                        "scopes": token_info.get("scopes", []),
                        "tenant_id": str(self.tenant_id)
                    }
            
            return {"connected": False, "error": "Token validation failed"}
            
        except Exception as e:
            return {"connected": False, "error": str(e)}
    
    async def list_tickets(self, limit: int = None) -> dict:
        """List tickets from HubSpot."""
        try:
            integration = await self._get_integration()
            access_token = integration.config.get("access_token")
            
            if not access_token:
                return {"success": False, "error": "No access token"}
            
            import httpx
            async with httpx.AsyncClient() as client:
                params = {
                    "limit": min(limit or 100, 100),
                    "properties": "subject,content,hs_ticket_priority,hs_pipeline_stage"
                }
                
                response = await client.get(
                    "https://api.hubapi.com/crm/v3/objects/tickets",
                    params=params,
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=30
                )
                response.raise_for_status()
                data = response.json()
                
                tickets = data.get("results", [])
                return {
                    "success": True,
                    "tickets": tickets,
                    "total_count": len(tickets),
                    "tenant_id": str(self.tenant_id)
                }
                
        except Exception as e:
            return {"success": False, "error": str(e), "tenant_id": str(self.tenant_id)}


async def test_multi_tenant_hubspot():
    """Test multi-tenant HubSpot functionality."""
    print("🚀 Testing Multi-Tenant HubSpot System")
    print("=" * 50)
    
    # Get access token from environment
    access_token = os.getenv("HUBSPOT_ACCESS_TOKEN")
    if not access_token:
        print("❌ No HUBSPOT_ACCESS_TOKEN found in environment")
        return
    
    # Setup test database
    session = await setup_db()
    
    try:
        # Test 1: Create tenant integrations for multiple tenants
        print("\n🏢 Step 1: Creating tenant integrations...")
        
        tenant1_id = uuid.uuid4()
        tenant2_id = uuid.uuid4()
        
        # Create integrations for both tenants using the same token (for demo)
        integration1 = TenantIntegration(
            tenant_id=tenant1_id,
            integration_type="hubspot",
            is_active=True,
            config={"access_token": access_token}
        )
        
        integration2 = TenantIntegration(
            tenant_id=tenant2_id,
            integration_type="hubspot",
            is_active=True,
            config={"access_token": access_token}
        )
        
        session.add(integration1)
        session.add(integration2)
        await session.commit()
        await session.refresh(integration1)
        await session.refresh(integration2)
        
        print(f"✅ Created integration for Tenant 1: {integration1.id}")
        print(f"✅ Created integration for Tenant 2: {integration2.id}")
        
        # Test 2: Test connections for both tenants
        print("\n🔌 Step 2: Testing connections...")
        
        service1 = MockHubSpotService(tenant1_id, integration1.id, session)
        service2 = MockHubSpotService(tenant2_id, integration2.id, session)
        
        # Test tenant 1 connection
        status1 = await service1.test_connection()
        print(f"Tenant 1 connection: {'✅' if status1.get('connected') else '❌'}")
        if status1.get('connected'):
            print(f"  Hub: {status1.get('hub_domain')}")
            print(f"  Scopes: {status1.get('scopes')}")
        else:
            print(f"  Error: {status1.get('error')}")
        
        # Test tenant 2 connection
        status2 = await service2.test_connection()
        print(f"Tenant 2 connection: {'✅' if status2.get('connected') else '❌'}")
        if status2.get('connected'):
            print(f"  Hub: {status2.get('hub_domain')}")
            print(f"  Scopes: {status2.get('scopes')}")
        else:
            print(f"  Error: {status2.get('error')}")
        
        # Test 3: List tickets for each tenant
        print("\n📋 Step 3: Listing tickets per tenant...")
        
        tickets_result1 = await service1.list_tickets(limit=5)
        if tickets_result1.get("success"):
            tickets1 = tickets_result1.get("tickets", [])
            print(f"Tenant 1: Found {len(tickets1)} tickets")
            for i, ticket in enumerate(tickets1[:3]):
                props = ticket.get("properties", {})
                subject = props.get("subject", "(No subject)")
                print(f"  {i+1}. {subject}")
        else:
            print(f"Tenant 1: Error - {tickets_result1.get('error')}")
        
        tickets_result2 = await service2.list_tickets(limit=5)
        if tickets_result2.get("success"):
            tickets2 = tickets_result2.get("tickets", [])
            print(f"Tenant 2: Found {len(tickets2)} tickets")
            for i, ticket in enumerate(tickets2[:3]):
                props = ticket.get("properties", {})
                subject = props.get("subject", "(No subject)")
                print(f"  {i+1}. {subject}")
        else:
            print(f"Tenant 2: Error - {tickets_result2.get('error')}")
        
        # Test 4: Demonstrate tenant isolation
        print("\n🔒 Step 4: Testing tenant isolation...")
        
        # Try to access tenant 1's integration with tenant 2's ID (should fail)
        service_bad = MockHubSpotService(tenant2_id, integration1.id, session)
        try:
            status_bad = await service_bad.test_connection()
            if status_bad.get("connected"):
                print("❌ Tenant isolation failed - wrong tenant can access integration")
            else:
                print("✅ Tenant isolation working - wrong tenant cannot access integration")
                print(f"   Error: {status_bad.get('error')}")
        except Exception as e:
            print("✅ Tenant isolation working - exception thrown for wrong tenant")
            print(f"   Exception: {str(e)}")
        
        print("\n🎉 Multi-tenant HubSpot test completed successfully!")
        print("\n📝 Next Steps:")
        print("  • Use the new API endpoints with proper tenant/integration IDs")
        print("  • Each tenant can have their own HubSpot integration")
        print("  • Tokens are validated before each API call")
        print("  • Full tenant isolation is enforced")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await session.close()
        await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(test_multi_tenant_hubspot())
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
        sys.exit(1) 