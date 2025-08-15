#!/usr/bin/env python3
"""
Check HubSpot Integrations Script

This script helps diagnose why HubSpot connections aren't persisting by:
1. Listing all existing HubSpot integrations
2. Testing their connection status
3. Showing token information (without exposing sensitive data)
4. Providing guidance on how to reuse existing integrations

Usage:
    python3 scripts/check_hubspot_integrations.py [tenant_id]
"""

from __future__ import annotations

import asyncio
import os
import sys
from typing import Optional
from uuid import UUID

import httpx
from dotenv import load_dotenv

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.db import get_db
from app.models.tenant_integration import TenantIntegration
from app.services.hubspot_service import create_hubspot_service
from sqlalchemy import select

load_dotenv()

BASE_URL = "http://localhost:8000"

async def check_integrations(tenant_id: Optional[str] = None) -> None:
    """Check all HubSpot integrations and their status."""
    
    print("🔍 Checking HubSpot Integrations")
    print("=" * 50)
    
    async for session in get_db():
        # Build query
        stmt = select(TenantIntegration).where(
            TenantIntegration.integration_type == "hubspot"
        )
        
        if tenant_id:
            stmt = stmt.where(TenantIntegration.tenant_id == UUID(tenant_id))
        
        result = await session.execute(stmt)
        integrations = result.scalars().all()
        
        if not integrations:
            print("❌ No HubSpot integrations found!")
            if tenant_id:
                print(f"   Tenant ID: {tenant_id}")
            else:
                print("   No integrations exist for any tenant")
            print("\n💡 To create a new integration:")
            print("   1. Use the OAuth flow: GET /api/hubspot/authorize/{tenant_id}")
            print("   2. Or create manually: POST /api/hubspot/integrations/{tenant_id}")
            return
        
        print(f"✅ Found {len(integrations)} HubSpot integration(s):\n")
        
        for i, integration in enumerate(integrations, 1):
            print(f"📋 Integration {i}:")
            print(f"   ID: {integration.id}")
            print(f"   Tenant ID: {integration.tenant_id}")
            print(f"   Active: {'✅' if integration.is_active else '❌'}")
            print(f"   Created: {integration.created_at}")
            print(f"   Last Sync: {integration.last_synced_at or 'Never'}")
            print(f"   Sync Status: {integration.last_sync_status or 'Unknown'}")
            
            # Check if token exists
            has_token = bool(integration.config.get("access_token"))
            print(f"   Has Token: {'✅' if has_token else '❌'}")
            
            if has_token:
                token = integration.config["access_token"]
                print(f"   Token Preview: {token[:10]}...{token[-10:]}")
            
            # Test connection
            print("   Testing connection...")
            try:
                service = create_hubspot_service(integration.tenant_id, integration.id)
                status = await service.test_connection(session)
                await service.close()
                
                if status.get("connected"):
                    print("   Connection: ✅ Connected")
                    if status.get("hub_domain"):
                        print(f"   Hub Domain: {status['hub_domain']}")
                    if status.get("scopes"):
                        print(f"   Scopes: {', '.join(status['scopes'])}")
                else:
                    print("   Connection: ❌ Failed")
                    if status.get("error"):
                        print(f"   Error: {status['error']}")
                    elif status.get("message"):
                        print(f"   Message: {status['message']}")
                        
            except Exception as e:
                print(f"   Connection: ❌ Error testing: {str(e)}")
            
            print()
        
        # Provide guidance
        print("💡 Integration Reuse Guide:")
        print("=" * 30)
        print("If you have active integrations above, you can reuse them instead of creating new ones:")
        print()
        print("1. Use existing integration ID in your API calls:")
        print("   GET /api/hubspot/status/{tenant_id}/{integration_id}")
        print("   GET /api/hubspot/tickets/{tenant_id}/{integration_id}")
        print()
        print("2. If tokens are expired, you can refresh them:")
        print("   - Use the OAuth flow again with the same integration")
        print("   - Or manually update the token in the database")
        print()
        print("3. To list integrations via API:")
        print(f"   GET {BASE_URL}/api/hubspot/integrations/{{tenant_id}}")
        
        break

async def test_api_endpoints(tenant_id: str) -> None:
    """Test the API endpoints to see if they work."""
    
    print(f"\n🧪 Testing API Endpoints for tenant {tenant_id}")
    print("=" * 50)
    
    async with httpx.AsyncClient() as client:
        # Test listing integrations
        print("Testing: GET /api/hubspot/integrations/{tenant_id}")
        try:
            response = await client.get(f"{BASE_URL}/api/hubspot/integrations/{tenant_id}")
            if response.status_code == 200:
                data = response.json()
                integrations = data.get("integrations", [])
                print(f"✅ Found {len(integrations)} integrations via API")
                
                for integration in integrations:
                    print(f"   - ID: {integration['id']}")
                    print(f"     Active: {integration['is_active']}")
                    if integration.get('connection_status'):
                        status = integration['connection_status']
                        print(f"     Connected: {status.get('connected', False)}")
            else:
                print(f"❌ API returned {response.status_code}: {response.text}")
        except Exception as e:
            print(f"❌ API call failed: {str(e)}")

def main():
    """Main function."""
    tenant_id = sys.argv[1] if len(sys.argv) > 1 else None
    
    if tenant_id:
        try:
            UUID(tenant_id)  # Validate UUID format
        except ValueError:
            print(f"❌ Invalid tenant ID format: {tenant_id}")
            print("   Tenant ID should be a valid UUID")
            sys.exit(1)
    
    print("🚀 HubSpot Integration Diagnostic Tool")
    print("=" * 50)
    
    # Check if app is running
    try:
        import httpx
        response = httpx.get(f"{BASE_URL}/health/", timeout=5)
        if response.status_code != 200:
            print(f"❌ App is running but health check failed: {response.status_code}")
            sys.exit(1)
    except Exception:
        print(f"❌ Cannot connect to app at {BASE_URL}")
        print("   Make sure the app is running: uvicorn app.main:app --reload")
        sys.exit(1)
    
    print("✅ App is running and healthy")
    
    # Run the checks
    asyncio.run(check_integrations(tenant_id))
    
    if tenant_id:
        asyncio.run(test_api_endpoints(tenant_id))

if __name__ == "__main__":
    main()
