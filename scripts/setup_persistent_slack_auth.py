#!/usr/bin/env python3
"""
Setup persistent Slack authentication.

This script helps set up and manage Slack OAuth integrations.

Usage:
    python3 scripts/setup_persistent_slack_auth.py [command] [tenant_id]

Commands:
    clean - Remove old/inactive Slack integrations
    status - Show current integration status
    test - Test OAuth configuration
    help - Show this help message
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
from sqlalchemy import and_, select, delete


async def clean_integrations(tenant_id: Optional[UUID] = None) -> None:
    """Clean up old or inactive Slack integrations."""
    print("🧹 Cleaning up Slack integrations...")
    print("-" * 40)
    
    session = AsyncSessionLocal()
    
    try:
        # Build query
        query = select(TenantIntegration).where(
            TenantIntegration.integration_type == "slack"
        )
        
        if tenant_id:
            query = query.where(TenantIntegration.tenant_id == tenant_id)
        
        result = await session.execute(query)
        integrations = result.scalars().all()
        
        if not integrations:
            print("✅ No Slack integrations found to clean up")
            return
        
        print(f"📊 Found {len(integrations)} Slack integration(s)")
        
        cleaned_count = 0
        for integration in integrations:
            config = integration.config or {}
            
            # Check if this is a legacy bot token integration
            if "token" in config and "access_token" not in config:
                print(f"🗑️  Removing legacy bot token integration: {integration.id}")
                await session.delete(integration)
                cleaned_count += 1
                continue
            
            # Check if integration is inactive
            if not integration.is_active:
                print(f"🗑️  Removing inactive integration: {integration.id}")
                await session.delete(integration)
                cleaned_count += 1
                continue
            
            # Check if token is expired and no refresh token
            if "access_token" in config:
                token_created_at = config.get("token_created_at")
                expires_in = config.get("expires_in", 3600)
                refresh_token = config.get("refresh_token")
                
                if token_created_at and not refresh_token:
                    try:
                        created_at = datetime.fromisoformat(token_created_at.replace('Z', '+00:00'))
                        expires_at = created_at.replace(tzinfo=timezone.utc) + timedelta(seconds=expires_in)
                        now = datetime.now(timezone.utc)
                        
                        if now >= expires_at:
                            print(f"🗑️  Removing expired integration without refresh token: {integration.id}")
                            await session.delete(integration)
                            cleaned_count += 1
                            continue
                    except Exception:
                        # If we can't parse the date, keep the integration
                        pass
        
        await session.commit()
        print(f"✅ Cleaned up {cleaned_count} integration(s)")
        
        # Show remaining integrations
        remaining_result = await session.execute(query)
        remaining = remaining_result.scalars().all()
        print(f"📊 {len(remaining)} integration(s) remaining")
        
    except Exception as e:
        print(f"❌ Error cleaning integrations: {e}")
    finally:
        await session.close()


async def show_status(tenant_id: Optional[UUID] = None) -> None:
    """Show current Slack integration status."""
    print("📊 Slack Integration Status")
    print("-" * 40)
    
    session = AsyncSessionLocal()
    
    try:
        # Build query
        query = select(TenantIntegration).where(
            TenantIntegration.integration_type == "slack"
        )
        
        if tenant_id:
            query = query.where(TenantIntegration.tenant_id == tenant_id)
        
        query = query.order_by(TenantIntegration.tenant_id, TenantIntegration.created_at)
        
        result = await session.execute(query)
        integrations = result.scalars().all()
        
        if not integrations:
            print("❌ No Slack integrations found")
            return
        
        print(f"📊 Found {len(integrations)} Slack integration(s)")
        print()
        
        # Group by tenant
        tenant_integrations = {}
        for integration in integrations:
            if integration.tenant_id not in tenant_integrations:
                tenant_integrations[integration.tenant_id] = []
            tenant_integrations[integration.tenant_id].append(integration)
        
        for tid, tenant_integrations_list in tenant_integrations.items():
            print(f"🏢 Tenant: {tid}")
            print("-" * 30)
            
            if len(tenant_integrations_list) > 1:
                print(f"⚠️  Multiple integrations found ({len(tenant_integrations_list)})")
            
            for i, integration in enumerate(tenant_integrations_list, 1):
                print(f"  Integration {i}:")
                print(f"    ID: {integration.id}")
                print(f"    Active: {'✅' if integration.is_active else '❌'}")
                print(f"    Created: {integration.created_at}")
                
                config = integration.config or {}
                
                if "access_token" in config:
                    print("    Type: OAuth (✅ Modern)")
                    access_token = config.get("access_token")
                    refresh_token = config.get("refresh_token")
                    expires_in = config.get("expires_in", 3600)
                    token_created_at = config.get("token_created_at")
                    team = config.get("team")
                    
                    print(f"    Access Token: {'✅ Present' if access_token else '❌ Missing'}")
                    print(f"    Refresh Token: {'✅ Present' if refresh_token else '❌ Missing'}")
                    print(f"    Team: {team or 'Unknown'}")
                    
                    if token_created_at:
                        try:
                            created_at = datetime.fromisoformat(token_created_at.replace('Z', '+00:00'))
                            expires_at = created_at.replace(tzinfo=timezone.utc) + timedelta(seconds=expires_in)
                            now = datetime.now(timezone.utc)
                            
                            if now >= expires_at:
                                print(f"    Status: ❌ EXPIRED")
                            elif now + timedelta(minutes=5) >= expires_at:
                                print(f"    Status: ⚠️  EXPIRING SOON")
                            else:
                                print(f"    Status: ✅ VALID")
                        except Exception:
                            print(f"    Status: ❓ UNKNOWN")
                    
                elif "token" in config:
                    print("    Type: Bot Token (⚠️  Legacy)")
                    token = config.get("token")
                    team = config.get("team")
                    print(f"    Bot Token: {'✅ Present' if token else '❌ Missing'}")
                    print(f"    Team: {team or 'Unknown'}")
                    print("    Note: Bot tokens don't support automatic refresh")
                
                print()
            
            print()
    
    except Exception as e:
        print(f"❌ Error showing status: {e}")
    finally:
        await session.close()


async def test_oauth_config() -> None:
    """Test OAuth configuration."""
    print("🔧 Testing OAuth Configuration")
    print("-" * 40)
    
    # Check environment variables
    client_id = os.getenv("SLACK_CLIENT_ID")
    client_secret = os.getenv("SLACK_CLIENT_SECRET")
    redirect_uri = os.getenv("SLACK_REDIRECT_URI")
    
    print("Environment Variables:")
    print(f"  SLACK_CLIENT_ID: {'✅ Set' if client_id else '❌ Missing'}")
    print(f"  SLACK_CLIENT_SECRET: {'✅ Set' if client_secret else '❌ Missing'}")
    print(f"  SLACK_REDIRECT_URI: {'✅ Set' if redirect_uri else '❌ Missing'}")
    
    if not all([client_id, client_secret, redirect_uri]):
        print()
        print("❌ Missing required environment variables")
        print()
        print("To fix this:")
        print("1. Create a Slack app at https://api.slack.com/apps")
        print("2. Configure OAuth settings:")
        print("   - Add redirect URL: http://localhost:8000/api/slack/oauth/callback")
        print("   - Add scopes: channels:read,channels:history,groups:read,groups:history")
        print("3. Install the app to your workspace")
        print("4. Copy Client ID and Client Secret to your .env file")
        return
    
    print()
    print("✅ OAuth configuration looks good!")
    print()
    print("Next steps:")
    print("1. Test the OAuth flow with a real workspace")
    print("2. Implement the frontend components")
    print("3. Test the complete user experience")


async def show_help() -> None:
    """Show help message."""
    print("🚀 Slack Persistent Authentication Setup")
    print("=" * 50)
    print()
    print("This script helps set up and manage Slack OAuth integrations.")
    print()
    print("Usage:")
    print("  python3 scripts/setup_persistent_slack_auth.py [command] [tenant_id]")
    print()
    print("Commands:")
    print("  clean   - Remove old/inactive Slack integrations")
    print("  status  - Show current integration status")
    print("  test    - Test OAuth configuration")
    print("  help    - Show this help message")
    print()
    print("Examples:")
    print("  python3 scripts/setup_persistent_slack_auth.py clean")
    print("  python3 scripts/setup_persistent_slack_auth.py status")
    print("  python3 scripts/setup_persistent_slack_auth.py test")
    print("  python3 scripts/setup_persistent_slack_auth.py clean 550e8400-e29b-41d4-a716-446655440000")
    print()
    print("Environment Variables Required:")
    print("  SLACK_CLIENT_ID - Your Slack app's client ID")
    print("  SLACK_CLIENT_SECRET - Your Slack app's client secret")
    print("  SLACK_REDIRECT_URI - OAuth redirect URI (e.g., http://localhost:8000/api/slack/oauth/callback)")


async def main() -> None:
    """Main function."""
    if len(sys.argv) < 2:
        await show_help()
        return
    
    command = sys.argv[1].lower()
    tenant_id = None
    
    if len(sys.argv) > 2:
        try:
            tenant_id = UUID(sys.argv[2])
        except ValueError:
            print("❌ Invalid tenant ID format")
            sys.exit(1)
    
    if command == "clean":
        await clean_integrations(tenant_id)
    elif command == "status":
        await show_status(tenant_id)
    elif command == "test":
        await test_oauth_config()
    elif command == "help":
        await show_help()
    else:
        print(f"❌ Unknown command: {command}")
        print()
        await show_help()


if __name__ == "__main__":
    asyncio.run(main())
