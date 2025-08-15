#!/usr/bin/env python3
"""
Test Persistent HubSpot Authentication

This script tests the new persistent authentication system that:
1. Stores refresh tokens for automatic token renewal
2. Automatically refreshes expired tokens
3. Provides endpoints to check authentication status

Usage:
    python3 scripts/test_persistent_auth.py [tenant_id]
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

async def test_auth_status(tenant_id: str) -> None:
    """Test the new auth-status endpoint."""
    
    print(f"🧪 Testing Auth Status for tenant {tenant_id}")
    print("=" * 50)
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/api/hubspot/auth-status/{tenant_id}")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ Auth Status Response:")
                print(f"   Authenticated: {data.get('authenticated')}")
                print(f"   Message: {data.get('message')}")
                print(f"   Needs Auth: {data.get('needs_auth')}")
                
                if data.get('integration_id'):
                    print(f"   Integration ID: {data['integration_id']}")
                
                if data.get('hub_domain'):
                    print(f"   Hub Domain: {data['hub_domain']}")
                
                if data.get('scopes'):
                    print(f"   Scopes: {', '.join(data['scopes'])}")
                
                if data.get('can_refresh'):
                    print(f"   Can Refresh: {data['can_refresh']}")
                
                return data
            else:
                print(f"❌ Auth Status failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Auth Status error: {str(e)}")
            return None

async def test_token_refresh(tenant_id: str, integration_id: str) -> None:
    """Test the token refresh endpoint."""
    
    print(f"\n🔄 Testing Token Refresh for integration {integration_id[:8]}...")
    print("=" * 50)
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{BASE_URL}/api/hubspot/refresh-token/{tenant_id}/{integration_id}")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ Token Refresh Response:")
                print(f"   Success: {data.get('success')}")
                print(f"   Message: {data.get('message')}")
                return True
            else:
                print(f"❌ Token Refresh failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Token Refresh error: {str(e)}")
            return False

async def test_connection_after_refresh(tenant_id: str, integration_id: str) -> None:
    """Test connection after token refresh."""
    
    print(f"\n🔗 Testing Connection After Refresh for integration {integration_id[:8]}...")
    print("=" * 50)
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/api/hubspot/status/{tenant_id}/{integration_id}")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ Connection Test Response:")
                print(f"   Connected: {data.get('connected')}")
                
                if data.get('hub_domain'):
                    print(f"   Hub Domain: {data['hub_domain']}")
                
                if data.get('scopes'):
                    print(f"   Scopes: {', '.join(data['scopes'])}")
                
                if data.get('error'):
                    print(f"   Error: {data['error']}")
                
                return data.get('connected', False)
            else:
                print(f"❌ Connection test failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Connection test error: {str(e)}")
            return False

async def check_integration_tokens(tenant_id: str) -> None:
    """Check the token information in the database."""
    
    print(f"\n📋 Checking Integration Tokens for tenant {tenant_id}")
    print("=" * 50)
    
    async for session in get_db():
        stmt = select(TenantIntegration).where(
            TenantIntegration.tenant_id == UUID(tenant_id),
            TenantIntegration.integration_type == "hubspot"
        ).order_by(TenantIntegration.created_at.desc())
        
        result = await session.execute(stmt)
        integrations = result.scalars().all()
        
        if not integrations:
            print("❌ No HubSpot integrations found")
            return
        
        print(f"✅ Found {len(integrations)} integration(s):\n")
        
        for i, integration in enumerate(integrations, 1):
            print(f"Integration {i}:")
            print(f"   ID: {integration.id}")
            print(f"   Active: {integration.is_active}")
            
            config = integration.config or {}
            has_access_token = bool(config.get("access_token"))
            has_refresh_token = bool(config.get("refresh_token"))
            expires_in = config.get("expires_in")
            token_created_at = config.get("token_created_at")
            
            print(f"   Has Access Token: {'✅' if has_access_token else '❌'}")
            print(f"   Has Refresh Token: {'✅' if has_refresh_token else '❌'}")
            
            if expires_in:
                print(f"   Expires In: {expires_in} seconds")
            
            if token_created_at:
                print(f"   Token Created: {token_created_at}")
            
            print()
        
        break

async def main():
    """Main function."""
    tenant_id = sys.argv[1] if len(sys.argv) > 1 else "550e8400-e29b-41d4-a716-446655440000"
    
    try:
        UUID(tenant_id)  # Validate UUID format
    except ValueError:
        print(f"❌ Invalid tenant ID format: {tenant_id}")
        print("   Tenant ID should be a valid UUID")
        sys.exit(1)
    
    print("🚀 Testing Persistent HubSpot Authentication")
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
    
    # Check integration tokens in database
    await check_integration_tokens(tenant_id)
    
    # Test auth status
    auth_data = await test_auth_status(tenant_id)
    
    if auth_data and not auth_data.get('authenticated') and auth_data.get('can_refresh'):
        # Try to refresh the token
        integration_id = auth_data.get('integration_id')
        if integration_id:
            refresh_success = await test_token_refresh(tenant_id, integration_id)
            
            if refresh_success:
                # Test connection after refresh
                await test_connection_after_refresh(tenant_id, integration_id)
                
                # Check auth status again
                print(f"\n🔄 Checking Auth Status After Refresh...")
                await test_auth_status(tenant_id)
    
    print(f"\n💡 Next Steps:")
    print("=" * 30)
    print("1. If authentication is working, users won't need to re-authenticate")
    print("2. Tokens will be automatically refreshed when they expire")
    print("3. The frontend can use /api/hubspot/auth-status/{tenant_id} to check if auth is needed")
    print("4. If tokens can't be refreshed, users will need to re-authenticate via OAuth")

if __name__ == "__main__":
    asyncio.run(main())
