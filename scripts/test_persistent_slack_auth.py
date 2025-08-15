#!/usr/bin/env python3
"""
Test persistent Slack authentication.

This script tests the Slack OAuth flow and token refresh functionality.

Usage:
    python3 scripts/test_persistent_slack_auth.py [tenant_id]
"""

import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import UUID

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import AsyncSessionLocal
from app.models.tenant_integration import TenantIntegration
from app.services.slack_service import SlackService
from sqlalchemy import and_, select


async def test_auth_status(tenant_id: UUID) -> None:
    """Test the auth status endpoint functionality."""
    print("🔍 Testing auth status...")
    print("-" * 40)
    
    session = AsyncSessionLocal()
    
    try:
        # Find active Slack integration for this tenant
        stmt = select(TenantIntegration).where(
            and_(
                TenantIntegration.tenant_id == tenant_id,
                TenantIntegration.integration_type == "slack",
                TenantIntegration.is_active == True
            )
        )
        result = await session.execute(stmt)
        integrations = result.scalars().all()
        
        if not integrations:
            print("❌ No active Slack integration found")
            return
        
        if len(integrations) > 1:
            print(f"⚠️  Multiple integrations found ({len(integrations)})")
            print("   Using the first one for testing")
        
        integration = integrations[0]
        print(f"✅ Found integration: {integration.id}")
        
        # Test the service's auth status logic
        service = SlackService(tenant_id, integration.id, session)
        
        try:
            # This should trigger token validation and refresh if needed
            token = await service._get_valid_token(session)
            print(f"✅ Token validation successful")
            print(f"   Token: {token[:20]}...")
            
            # Test API call
            print("🔍 Testing API call...")
            result = await service.list_channels(integration.id)
            if result.get("success"):
                channels = result.get("channels", [])
                print(f"✅ API call successful - found {len(channels)} channels")
            else:
                print(f"❌ API call failed: {result.get('error')}")
                
        except ValueError as e:
            print(f"❌ Token validation failed: {e}")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
        finally:
            await service.close()
    
    except Exception as e:
        print(f"❌ Error testing auth status: {e}")
    finally:
        await session.close()


async def test_token_refresh(tenant_id: UUID) -> None:
    """Test token refresh functionality."""
    print("\n🔄 Testing token refresh...")
    print("-" * 40)
    
    session = AsyncSessionLocal()
    
    try:
        # Find active Slack integration
        stmt = select(TenantIntegration).where(
            and_(
                TenantIntegration.tenant_id == tenant_id,
                TenantIntegration.integration_type == "slack",
                TenantIntegration.is_active == True
            )
        )
        result = await session.execute(stmt)
        integration = result.scalars().first()
        
        if not integration:
            print("❌ No active Slack integration found")
            return
        
        config = integration.config or {}
        refresh_token = config.get("refresh_token")
        
        if not refresh_token:
            print("❌ No refresh token available")
            return
        
        print(f"✅ Found refresh token: {refresh_token[:20]}...")
        
        # Test manual refresh
        service = SlackService(tenant_id, integration.id, session)
        
        try:
            print("🔄 Attempting token refresh...")
            new_token = await service._refresh_access_token(session, integration, refresh_token)
            
            if new_token:
                print(f"✅ Token refresh successful")
                print(f"   New token: {new_token[:20]}...")
                
                # Check if the integration was updated
                await session.refresh(integration)
                updated_config = integration.config or {}
                new_expires_in = updated_config.get("expires_in")
                new_created_at = updated_config.get("token_created_at")
                
                print(f"   Expires in: {new_expires_in} seconds")
                print(f"   Created at: {new_created_at}")
            else:
                print("❌ Token refresh failed")
                
        except Exception as e:
            print(f"❌ Error during token refresh: {e}")
        finally:
            await service.close()
    
    except Exception as e:
        print(f"❌ Error testing token refresh: {e}")
    finally:
        await session.close()


async def test_oauth_flow(tenant_id: UUID) -> None:
    """Test OAuth flow setup."""
    print("\n🔗 Testing OAuth flow setup...")
    print("-" * 40)
    
    # Check environment variables
    client_id = os.getenv("SLACK_CLIENT_ID")
    client_secret = os.getenv("SLACK_CLIENT_SECRET")
    redirect_uri = os.getenv("SLACK_REDIRECT_URI")
    
    if not all([client_id, client_secret, redirect_uri]):
        print("❌ Missing OAuth environment variables")
        print("   Please set SLACK_CLIENT_ID, SLACK_CLIENT_SECRET, and SLACK_REDIRECT_URI")
        return
    
    print("✅ OAuth environment variables configured")
    print(f"   Client ID: {client_id}")
    print(f"   Redirect URI: {redirect_uri}")
    
    # Test authorization URL generation
    session = AsyncSessionLocal()
    
    try:
        # Create a temporary integration for testing
        integration = TenantIntegration(
            tenant_id=tenant_id,
            integration_type="slack",
            is_active=False,
            config={"oauth_state": "testing"}
        )
        session.add(integration)
        await session.commit()
        await session.refresh(integration)
        
        print(f"✅ Created test integration: {integration.id}")
        
        # Build authorization URL
        scopes = "channels:read,channels:history,groups:read,groups:history"
        state = f"{tenant_id}:{integration.id}"
        
        auth_url = (
            f"https://slack.com/oauth/v2/authorize"
            f"?client_id={client_id}"
            f"&scope={scopes}"
            f"&redirect_uri={redirect_uri}"
            f"&state={state}"
        )
        
        print("✅ Authorization URL generated:")
        print(f"   {auth_url}")
        
        # Clean up test integration
        await session.delete(integration)
        await session.commit()
        print("✅ Test integration cleaned up")
        
    except Exception as e:
        print(f"❌ Error testing OAuth flow: {e}")
    finally:
        await session.close()


async def test_integration_creation(tenant_id: UUID) -> None:
    """Test creating a new OAuth integration."""
    print("\n➕ Testing OAuth integration creation...")
    print("-" * 40)
    
    session = AsyncSessionLocal()
    
    try:
        service = SlackService(tenant_id, session=session)
        
        # Test with mock OAuth tokens (these won't work but test the structure)
        mock_access_token = "xoxp-mock-access-token"
        mock_refresh_token = "xoxp-mock-refresh-token"
        
        result = await service.create_oauth_integration(
            access_token=mock_access_token,
            refresh_token=mock_refresh_token,
            team="Test Workspace",
            expires_in=3600
        )
        
        if result.get("success"):
            integration_id = result.get("integration_id")
            print(f"✅ OAuth integration created: {integration_id}")
            
            # Clean up
            integration = await session.get(TenantIntegration, UUID(integration_id))
            if integration:
                await session.delete(integration)
                await session.commit()
                print("✅ Test integration cleaned up")
        else:
            print(f"❌ Failed to create OAuth integration: {result.get('error')}")
    
    except Exception as e:
        print(f"❌ Error testing integration creation: {e}")
    finally:
        await session.close()


async def main() -> None:
    """Main function."""
    if len(sys.argv) > 1:
        try:
            tenant_id = UUID(sys.argv[1])
        except ValueError:
            print("❌ Invalid tenant ID format")
            sys.exit(1)
    else:
        # Use a default tenant ID for testing
        tenant_id = UUID("550e8400-e29b-41d4-a716-446655440000")
        print(f"ℹ️  Using default tenant ID: {tenant_id}")
        print("   You can specify a different tenant ID as an argument")
    
    print("🚀 Testing Persistent Slack Authentication")
    print("=" * 60)
    print(f"Tenant ID: {tenant_id}")
    print()
    
    await test_oauth_flow(tenant_id)
    await test_integration_creation(tenant_id)
    await test_auth_status(tenant_id)
    await test_token_refresh(tenant_id)
    
    print("\n✅ All tests complete!")
    print("\nNext steps:")
    print("1. Set up your Slack app with OAuth credentials")
    print("2. Test the actual OAuth flow with a real workspace")
    print("3. Implement the frontend components")
    print("4. Test the complete user experience")


if __name__ == "__main__":
    asyncio.run(main())
