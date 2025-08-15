#!/usr/bin/env python3
"""
Reuse HubSpot Integration Script

This script helps you reuse existing HubSpot integrations instead of creating new ones.
It will:
1. List your existing integrations
2. Let you select one to use
3. Show you the exact API calls to make with that integration

Usage:
    python3 scripts/reuse_hubspot_integration.py [tenant_id]
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
from sqlalchemy import select

load_dotenv()

BASE_URL = "http://localhost:8000"

async def list_integrations(tenant_id: Optional[str] = None) -> list[dict]:
    """List all HubSpot integrations and return them as a list."""
    
    async for session in get_db():
        stmt = select(TenantIntegration).where(
            TenantIntegration.integration_type == "hubspot"
        )
        
        if tenant_id:
            stmt = stmt.where(TenantIntegration.tenant_id == UUID(tenant_id))
        
        result = await session.execute(stmt)
        integrations = result.scalars().all()
        
        integration_list = []
        for integration in integrations:
            integration_data = {
                "id": str(integration.id),
                "tenant_id": str(integration.tenant_id),
                "is_active": integration.is_active,
                "has_token": bool(integration.config.get("access_token")),
                "last_synced_at": integration.last_synced_at,
                "last_sync_status": integration.last_sync_status,
                "created_at": integration.created_at
            }
            integration_list.append(integration_data)
        
        return integration_list

async def test_integration(tenant_id: str, integration_id: str) -> dict:
    """Test a specific integration and return its status."""
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/api/hubspot/status/{tenant_id}/{integration_id}")
            if response.status_code == 200:
                return response.json()
            else:
                return {"connected": False, "error": f"API returned {response.status_code}"}
        except Exception as e:
            return {"connected": False, "error": str(e)}

def print_integration_commands(tenant_id: str, integration_id: str) -> None:
    """Print the exact commands to use this integration."""
    
    print(f"\n🚀 Ready to use Integration {integration_id[:8]}...")
    print("=" * 50)
    print("Use these exact API calls with your integration:")
    print()
    
    print("1. Test Connection:")
    print(f"   curl -X GET '{BASE_URL}/api/hubspot/status/{tenant_id}/{integration_id}'")
    print()
    
    print("2. List Tickets:")
    print(f"   curl -X GET '{BASE_URL}/api/hubspot/tickets/{tenant_id}/{integration_id}?limit=10'")
    print()
    
    print("3. Start Full Sync:")
    print(f"   curl -X POST '{BASE_URL}/api/hubspot/sync/{tenant_id}/{integration_id}/full'")
    print()
    
    print("4. List Integration Details:")
    print(f"   curl -X GET '{BASE_URL}/api/hubspot/integrations/{tenant_id}'")
    print()
    
    print("5. Frontend Integration (if you have a frontend):")
    print(f"   GET {BASE_URL}/api/hubspot/status/{tenant_id}/{integration_id}")
    print(f"   GET {BASE_URL}/api/hubspot/tickets/{tenant_id}/{integration_id}")
    print()
    
    print("💡 Pro Tips:")
    print("   - Save the integration_id and tenant_id for future use")
    print("   - The integration will persist across app restarts")
    print("   - If the token expires, you can refresh it via OAuth")
    print("   - You can have multiple integrations per tenant")

async def main():
    """Main function."""
    tenant_id = sys.argv[1] if len(sys.argv) > 1 else None
    
    if tenant_id:
        try:
            UUID(tenant_id)  # Validate UUID format
        except ValueError:
            print(f"❌ Invalid tenant ID format: {tenant_id}")
            print("   Tenant ID should be a valid UUID")
            sys.exit(1)
    
    print("🔍 HubSpot Integration Reuse Tool")
    print("=" * 50)
    
    # Check if app is running
    try:
        response = httpx.get(f"{BASE_URL}/health/", timeout=5)
        if response.status_code != 200:
            print(f"❌ App is running but health check failed: {response.status_code}")
            sys.exit(1)
    except Exception:
        print(f"❌ Cannot connect to app at {BASE_URL}")
        print("   Make sure the app is running: uvicorn app.main:app --reload")
        sys.exit(1)
    
    print("✅ App is running and healthy")
    
    # List integrations
    integrations = await list_integrations(tenant_id)
    
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
    
    # Display integrations
    for i, integration in enumerate(integrations, 1):
        status_icon = "✅" if integration["is_active"] else "❌"
        token_icon = "✅" if integration["has_token"] else "❌"
        
        print(f"{i}. {status_icon} Integration {integration['id'][:8]}...")
        print(f"   Tenant: {integration['tenant_id']}")
        print(f"   Active: {integration['is_active']}")
        print(f"   Has Token: {integration['has_token']}")
        print(f"   Last Sync: {integration['last_synced_at'] or 'Never'}")
        print(f"   Status: {integration['last_sync_status'] or 'Unknown'}")
        print()
    
    # Let user select an integration
    if len(integrations) == 1:
        selected = integrations[0]
        print("🎯 Only one integration found - using it automatically")
    else:
        try:
            choice = input(f"Select integration (1-{len(integrations)}): ").strip()
            choice_idx = int(choice) - 1
            if choice_idx < 0 or choice_idx >= len(integrations):
                print("❌ Invalid selection")
                return
            selected = integrations[choice_idx]
        except (ValueError, KeyboardInterrupt):
            print("\n❌ Invalid selection or cancelled")
            return
    
    # Test the selected integration
    print(f"\n🧪 Testing integration {selected['id'][:8]}...")
    status = await test_integration(selected['tenant_id'], selected['id'])
    
    if status.get("connected"):
        print("✅ Integration is working!")
        if status.get("hub_domain"):
            print(f"   Connected to: {status['hub_domain']}")
    else:
        print("❌ Integration has issues:")
        if status.get("error"):
            print(f"   Error: {status['error']}")
        elif status.get("message"):
            print(f"   Message: {status['message']}")
        
        print("\n💡 To fix this integration:")
        print("   1. Try the OAuth flow again to refresh the token")
        print("   2. Or create a new integration if this one is broken")
        return
    
    # Show commands
    print_integration_commands(selected['tenant_id'], selected['id'])

if __name__ == "__main__":
    asyncio.run(main())
