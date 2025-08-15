#!/usr/bin/env python3
"""
Setup Persistent HubSpot Authentication

This script helps set up persistent authentication by:
1. Cleaning up old integrations that don't have refresh tokens
2. Providing guidance on creating a new integration with refresh tokens
3. Testing the new persistent authentication system

Usage:
    python3 scripts/setup_persistent_auth.py [tenant_id]
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
from sqlalchemy import select, delete

load_dotenv()

BASE_URL = "http://localhost:8000"

async def cleanup_old_integrations(tenant_id: str) -> None:
    """Clean up old integrations that don't have refresh tokens."""
    
    print(f"🧹 Cleaning up old integrations for tenant {tenant_id}")
    print("=" * 50)
    
    async for session in get_db():
        # Find integrations without refresh tokens
        stmt = select(TenantIntegration).where(
            TenantIntegration.tenant_id == UUID(tenant_id),
            TenantIntegration.integration_type == "hubspot"
        )
        
        result = await session.execute(stmt)
        integrations = result.scalars().all()
        
        integrations_to_delete = []
        for integration in integrations:
            config = integration.config or {}
            has_refresh_token = bool(config.get("refresh_token"))
            
            if not has_refresh_token:
                integrations_to_delete.append(integration)
                print(f"   Will delete: {integration.id} (no refresh token)")
        
        if not integrations_to_delete:
            print("   No old integrations to clean up")
            return
        
        # Ask for confirmation
        response = input(f"\nDelete {len(integrations_to_delete)} old integration(s)? (y/N): ").strip().lower()
        
        if response == 'y':
            for integration in integrations_to_delete:
                await session.delete(integration)
            
            await session.commit()
            print(f"✅ Deleted {len(integrations_to_delete)} old integration(s)")
        else:
            print("❌ Cleanup cancelled")
        
        break

async def check_environment() -> bool:
    """Check if the environment is properly configured for OAuth."""
    
    print("🔧 Checking Environment Configuration")
    print("=" * 50)
    
    required_vars = [
        "HUBSPOT_CLIENT_ID",
        "HUBSPOT_CLIENT_SECRET", 
        "HUBSPOT_REDIRECT_URI"
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
        else:
            print(f"   ✅ {var}: {value[:10]}..." if len(value) > 10 else f"   ✅ {var}: {value}")
    
    if missing_vars:
        print(f"\n❌ Missing environment variables: {', '.join(missing_vars)}")
        print("   Please add these to your .env file")
        return False
    
    print("\n✅ Environment is properly configured")
    return True

def print_setup_instructions(tenant_id: str) -> None:
    """Print instructions for setting up persistent authentication."""
    
    print(f"\n📋 Setup Instructions for Persistent Authentication")
    print("=" * 50)
    print("To enable persistent authentication, you need to create a new HubSpot integration")
    print("that includes refresh tokens. Here's how:")
    print()
    print("1. Start the OAuth flow:")
    print(f"   GET {BASE_URL}/api/hubspot/authorize/{tenant_id}")
    print()
    print("2. Complete the OAuth flow in your browser")
    print("3. The new integration will store both access and refresh tokens")
    print("4. Tokens will be automatically refreshed when they expire")
    print()
    print("Frontend Integration:")
    print("=====================")
    print("1. Check auth status before showing connect button:")
    print(f"   GET {BASE_URL}/api/hubspot/auth-status/{tenant_id}")
    print()
    print("2. If authenticated, use existing integration")
    print("3. If not authenticated, start OAuth flow")
    print()
    print("Example Frontend Flow:")
    print("======================")
    print("```javascript")
    print("// Check if user is already authenticated")
    print("const authStatus = await api.get(`/api/hubspot/auth-status/${tenantId}`);")
    print("")
    print("if (authStatus.data.authenticated) {")
    print("  // User is authenticated, show dashboard")
    print("  showDashboard();")
    print("} else if (authStatus.data.can_refresh) {")
    print("  // Try to refresh token")
    print("  await api.post(`/api/hubspot/refresh-token/${tenantId}/${integrationId}`);")
    print("  showDashboard();")
    print("} else {")
    print("  // User needs to authenticate")
    print("  showConnectButton();")
    print("}")
    print("```")

async def test_new_endpoints(tenant_id: str) -> None:
    """Test the new endpoints after setup."""
    
    print(f"\n🧪 Testing New Endpoints")
    print("=" * 50)
    
    async with httpx.AsyncClient() as client:
        # Test auth status endpoint
        print("Testing auth-status endpoint...")
        try:
            response = await client.get(f"{BASE_URL}/api/hubspot/auth-status/{tenant_id}")
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Auth Status: {data.get('authenticated')}")
                print(f"   Message: {data.get('message')}")
            else:
                print(f"   ❌ Auth Status failed: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Auth Status error: {str(e)}")
        
        # Test authorize endpoint
        print("\nTesting authorize endpoint...")
        try:
            response = await client.get(f"{BASE_URL}/api/hubspot/authorize/{tenant_id}")
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Authorize URL generated")
                print(f"   Integration ID: {data.get('integration_id')}")
                print(f"   Auth URL: {data.get('authorization_url')[:50]}...")
            else:
                print(f"   ❌ Authorize failed: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Authorize error: {str(e)}")

async def main():
    """Main function."""
    tenant_id = sys.argv[1] if len(sys.argv) > 1 else "550e8400-e29b-41d4-a716-446655440000"
    
    try:
        UUID(tenant_id)  # Validate UUID format
    except ValueError:
        print(f"❌ Invalid tenant ID format: {tenant_id}")
        print("   Tenant ID should be a valid UUID")
        sys.exit(1)
    
    print("🚀 Setting up Persistent HubSpot Authentication")
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
    
    # Check environment
    if not await check_environment():
        sys.exit(1)
    
    # Clean up old integrations
    await cleanup_old_integrations(tenant_id)
    
    # Print setup instructions
    print_setup_instructions(tenant_id)
    
    # Test new endpoints
    await test_new_endpoints(tenant_id)
    
    print(f"\n🎉 Setup Complete!")
    print("=" * 30)
    print("Next steps:")
    print("1. Create a new HubSpot integration via OAuth")
    print("2. The new integration will support persistent authentication")
    print("3. Update your frontend to use the new auth-status endpoint")
    print("4. Users will only need to authenticate once!")

if __name__ == "__main__":
    asyncio.run(main())
