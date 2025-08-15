#!/usr/bin/env python3
"""
Check Slack integration status for all tenants.

This script helps diagnose Slack integration issues by checking:
- Integration records in the database
- Token validity and expiration
- OAuth configuration
- API connectivity

Usage:
    python3 scripts/check_slack_integrations.py
"""

import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from uuid import UUID

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import AsyncSessionLocal
from app.models.tenant_integration import TenantIntegration
from app.services.slack_service import SlackService
from sqlalchemy import and_, select


async def check_slack_integrations() -> None:
    """Check all Slack integrations in the database."""
    print("🔍 Checking Slack integrations...")
    print("=" * 60)
    
    session = AsyncSessionLocal()
    
    try:
        # Get all Slack integrations
        stmt = select(TenantIntegration).where(
            TenantIntegration.integration_type == "slack"
        ).order_by(TenantIntegration.tenant_id, TenantIntegration.created_at)
        
        result = await session.execute(stmt)
        integrations = result.scalars().all()
        
        if not integrations:
            print("❌ No Slack integrations found in the database")
            return
        
        print(f"📊 Found {len(integrations)} Slack integration(s)")
        print()
        
        # Group by tenant
        tenant_integrations: Dict[UUID, List[TenantIntegration]] = {}
        for integration in integrations:
            if integration.tenant_id not in tenant_integrations:
                tenant_integrations[integration.tenant_id] = []
            tenant_integrations[integration.tenant_id].append(integration)
        
        for tenant_id, tenant_integrations_list in tenant_integrations.items():
            print(f"🏢 Tenant: {tenant_id}")
            print("-" * 40)
            
            if len(tenant_integrations_list) > 1:
                print(f"⚠️  WARNING: Multiple integrations found ({len(tenant_integrations_list)})")
                print("   Consider cleaning up duplicates")
                print()
            
            for i, integration in enumerate(tenant_integrations_list, 1):
                print(f"Integration {i}:")
                print(f"  ID: {integration.id}")
                print(f"  Active: {'✅' if integration.is_active else '❌'}")
                print(f"  Created: {integration.created_at}")
                print(f"  Updated: {integration.updated_at}")
                
                config = integration.config or {}
                
                # Check token type
                if "access_token" in config:
                    print("  Type: OAuth (✅ Modern)")
                    access_token = config.get("access_token")
                    refresh_token = config.get("refresh_token")
                    expires_in = config.get("expires_in", 3600)
                    token_created_at = config.get("token_created_at")
                    
                    print(f"  Access Token: {'✅ Present' if access_token else '❌ Missing'}")
                    print(f"  Refresh Token: {'✅ Present' if refresh_token else '❌ Missing'}")
                    print(f"  Expires In: {expires_in} seconds")
                    
                    if token_created_at:
                        try:
                            created_at = datetime.fromisoformat(token_created_at.replace('Z', '+00:00'))
                            expires_at = created_at.replace(tzinfo=timezone.utc) + timedelta(seconds=expires_in)
                            now = datetime.now(timezone.utc)
                            
                            if now >= expires_at:
                                print(f"  Token Status: ❌ EXPIRED ({expires_at})")
                            elif now + timedelta(minutes=5) >= expires_at:
                                print(f"  Token Status: ⚠️  EXPIRING SOON ({expires_at})")
                            else:
                                print(f"  Token Status: ✅ VALID (expires {expires_at})")
                        except Exception as e:
                            print(f"  Token Status: ❓ UNKNOWN (error parsing date: {e})")
                    else:
                        print("  Token Status: ❓ UNKNOWN (no creation date)")
                    
                    # Test API connectivity
                    if integration.is_active:
                        print("  Testing API connectivity...")
                        try:
                            service = SlackService(tenant_id, integration.id, session)
                            await service._get_valid_token(session)
                            print("  API Test: ✅ SUCCESS")
                        except Exception as e:
                            print(f"  API Test: ❌ FAILED - {str(e)}")
                        finally:
                            await service.close()
                    
                elif "token" in config:
                    print("  Type: Bot Token (⚠️  Legacy)")
                    token = config.get("token")
                    print(f"  Bot Token: {'✅ Present' if token else '❌ Missing'}")
                    print("  Note: Bot tokens don't support automatic refresh")
                    
                    # Test API connectivity
                    if integration.is_active and token:
                        print("  Testing API connectivity...")
                        try:
                            service = SlackService(tenant_id, integration.id, session)
                            # For bot tokens, we need to use the legacy method
                            result = await service.list_channels(integration.id)
                            if result.get("success"):
                                print("  API Test: ✅ SUCCESS")
                            else:
                                print(f"  API Test: ❌ FAILED - {result.get('error', 'Unknown error')}")
                        except Exception as e:
                            print(f"  API Test: ❌ FAILED - {str(e)}")
                        finally:
                            await service.close()
                else:
                    print("  Type: ❓ UNKNOWN (no tokens found)")
                
                print()
            
            print()
    
    except Exception as e:
        print(f"❌ Error checking integrations: {e}")
    finally:
        await session.close()


async def check_oauth_config() -> None:
    """Check if OAuth configuration is properly set up."""
    print("🔧 Checking OAuth Configuration...")
    print("=" * 60)
    
    required_vars = [
        "SLACK_CLIENT_ID",
        "SLACK_CLIENT_SECRET", 
        "SLACK_REDIRECT_URI"
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Mask the secret
            if "SECRET" in var:
                print(f"✅ {var}: {'*' * len(value)}")
            else:
                print(f"✅ {var}: {value}")
        else:
            print(f"❌ {var}: NOT SET")
            missing_vars.append(var)
    
    if missing_vars:
        print()
        print("⚠️  Missing environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print()
        print("To fix this:")
        print("1. Create a Slack app at https://api.slack.com/apps")
        print("2. Configure OAuth settings with redirect URI")
        print("3. Add the environment variables to your .env file")
    else:
        print()
        print("✅ OAuth configuration looks good!")
    
    print()


async def main() -> None:
    """Main function."""
    print("🚀 Slack Integration Checker")
    print("=" * 60)
    print()
    
    await check_oauth_config()
    await check_slack_integrations()
    
    print("✅ Check complete!")


if __name__ == "__main__":
    asyncio.run(main())
