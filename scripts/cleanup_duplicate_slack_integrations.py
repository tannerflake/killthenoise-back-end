#!/usr/bin/env python3
"""
Script to clean up duplicate Slack integrations for a specific tenant.

This script will:
1. Find all Slack integrations for the specified tenant
2. Identify duplicates based on configuration
3. Keep the most recent/active integration
4. Deactivate or delete duplicate integrations
"""

import asyncio
import sys
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

# Add the app directory to the path so we can import our modules
sys.path.append(".")

from app.db import AsyncSessionLocal
from app.models.tenant_integration import TenantIntegration


async def get_slack_integrations(session: AsyncSession, tenant_id: UUID) -> List[TenantIntegration]:
    """Get all Slack integrations for a tenant."""
    stmt = select(TenantIntegration).where(
        and_(
            TenantIntegration.tenant_id == tenant_id,
            TenantIntegration.integration_type == "slack"
        )
    ).order_by(TenantIntegration.created_at.desc())
    
    result = await session.execute(stmt)
    return result.scalars().all()


def analyze_integrations(integrations: List[TenantIntegration]) -> dict:
    """Analyze integrations to identify duplicates and determine which to keep."""
    if len(integrations) <= 1:
        return {
            "has_duplicates": False,
            "integrations": integrations,
            "to_keep": integrations[0] if integrations else None,
            "to_remove": []
        }
    
    # Group integrations by their key characteristics
    integration_groups = {}
    
    for integration in integrations:
        config = integration.config or {}
        
        # Create a key based on the type of integration (OAuth vs legacy token)
        if "access_token" in config and "refresh_token" in config:
            # OAuth integration
            key = "oauth"
        elif "token" in config:
            # Legacy bot token integration
            key = "legacy"
        else:
            # Invalid/incomplete integration
            key = "invalid"
        
        if key not in integration_groups:
            integration_groups[key] = []
        integration_groups[key].append(integration)
    
    # Determine which integrations to keep and remove
    to_keep = None
    to_remove = []
    
    # Prefer OAuth integrations over legacy ones
    if "oauth" in integration_groups:
        oauth_integrations = integration_groups["oauth"]
        # Keep the most recent active OAuth integration
        active_oauth = [i for i in oauth_integrations if i.is_active]
        if active_oauth:
            to_keep = max(active_oauth, key=lambda x: x.created_at)
            to_remove.extend([i for i in oauth_integrations if i != to_keep])
        else:
            to_keep = max(oauth_integrations, key=lambda x: x.created_at)
            to_remove.extend([i for i in oauth_integrations if i != to_keep])
    
    # If no OAuth integrations, keep the most recent legacy integration
    elif "legacy" in integration_groups:
        legacy_integrations = integration_groups["legacy"]
        to_keep = max(legacy_integrations, key=lambda x: x.created_at)
        to_remove.extend([i for i in legacy_integrations if i != to_keep])
    
    # Add all invalid integrations to removal list
    if "invalid" in integration_groups:
        to_remove.extend(integration_groups["invalid"])
    
    return {
        "has_duplicates": len(to_remove) > 0,
        "integrations": integrations,
        "to_keep": to_keep,
        "to_remove": to_remove,
        "groups": integration_groups
    }


async def cleanup_duplicates(session: AsyncSession, tenant_id: UUID, dry_run: bool = True) -> dict:
    """Clean up duplicate Slack integrations for a tenant."""
    print(f"Analyzing Slack integrations for tenant: {tenant_id}")
    print(f"Dry run mode: {'ON' if dry_run else 'OFF'}")
    print("-" * 60)
    
    # Get all Slack integrations
    integrations = await get_slack_integrations(session, tenant_id)
    
    if not integrations:
        print("No Slack integrations found for this tenant.")
        return {"status": "no_integrations", "message": "No Slack integrations found"}
    
    print(f"Found {len(integrations)} Slack integration(s):")
    for i, integration in enumerate(integrations, 1):
        config = integration.config or {}
        integration_type = "OAuth" if "access_token" in config else "Legacy Bot Token" if "token" in config else "Invalid"
        status = "Active" if integration.is_active else "Inactive"
        print(f"  {i}. ID: {integration.id}")
        print(f"     Type: {integration_type}")
        print(f"     Status: {status}")
        print(f"     Created: {integration.created_at}")
        print(f"     Last Updated: {integration.updated_at}")
        if config.get("team"):
            print(f"     Team: {config.get('team')}")
        print()
    
    # Analyze for duplicates
    analysis = analyze_integrations(integrations)
    
    if not analysis["has_duplicates"]:
        print("No duplicate integrations found. All integrations are unique.")
        return {"status": "no_duplicates", "message": "No duplicates found"}
    
    print("DUPLICATE INTEGRATIONS DETECTED:")
    print("-" * 60)
    
    if analysis["to_keep"]:
        config = analysis["to_keep"].config or {}
        integration_type = "OAuth" if "access_token" in config else "Legacy Bot Token"
        print(f"KEEPING: {analysis['to_keep'].id} ({integration_type})")
        print(f"  - Created: {analysis['to_keep'].created_at}")
        print(f"  - Status: {'Active' if analysis['to_keep'].is_active else 'Inactive'}")
        if config.get("team"):
            print(f"  - Team: {config.get('team')}")
        print()
    
    print("REMOVING:")
    for integration in analysis["to_remove"]:
        config = integration.config or {}
        integration_type = "OAuth" if "access_token" in config else "Legacy Bot Token" if "token" in config else "Invalid"
        print(f"  - {integration.id} ({integration_type})")
        print(f"    Created: {integration.created_at}")
        print(f"    Status: {'Active' if integration.is_active else 'Inactive'}")
        if config.get("team"):
            print(f"    Team: {config.get('team')}")
        print()
    
    if dry_run:
        print("DRY RUN - No changes made. Run with --execute to perform cleanup.")
        return {
            "status": "dry_run",
            "to_keep": analysis["to_keep"].id if analysis["to_keep"] else None,
            "to_remove": [i.id for i in analysis["to_remove"]],
            "message": "Dry run completed"
        }
    
    # Perform the cleanup
    print("PERFORMING CLEANUP...")
    print("-" * 60)
    
    try:
        # Deactivate all integrations first
        await session.execute(
            update(TenantIntegration)
            .where(TenantIntegration.tenant_id == tenant_id)
            .where(TenantIntegration.integration_type == "slack")
            .values(is_active=False)
        )
        
        # Reactivate the one we want to keep
        if analysis["to_keep"]:
            await session.execute(
                update(TenantIntegration)
                .where(TenantIntegration.id == analysis["to_keep"].id)
                .values(is_active=True)
            )
        
        # Delete the duplicate integrations
        for integration in analysis["to_remove"]:
            await session.execute(
                delete(TenantIntegration)
                .where(TenantIntegration.id == integration.id)
            )
        
        await session.commit()
        
        print("✅ Cleanup completed successfully!")
        print(f"Kept integration: {analysis['to_keep'].id if analysis['to_keep'] else 'None'}")
        print(f"Removed {len(analysis['to_remove'])} duplicate integration(s)")
        
        return {
            "status": "success",
            "to_keep": analysis["to_keep"].id if analysis["to_keep"] else None,
            "to_remove": [i.id for i in analysis["to_remove"]],
            "message": "Cleanup completed successfully"
        }
        
    except Exception as e:
        await session.rollback()
        print(f"❌ Error during cleanup: {str(e)}")
        return {
            "status": "error",
            "message": f"Cleanup failed: {str(e)}"
        }


async def main():
    """Main function to run the cleanup script."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Clean up duplicate Slack integrations")
    parser.add_argument("--tenant-id", required=True, help="Tenant ID to clean up")
    parser.add_argument("--execute", action="store_true", help="Actually perform the cleanup (default is dry run)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes (default)")
    
    args = parser.parse_args()
    
    try:
        tenant_id = UUID(args.tenant_id)
    except ValueError:
        print(f"Error: Invalid tenant ID format: {args.tenant_id}")
        sys.exit(1)
    
    # Determine if this is a dry run
    dry_run = not args.execute
    
    async with AsyncSessionLocal() as session:
        result = await cleanup_duplicates(session, tenant_id, dry_run=dry_run)
        
        if result["status"] == "error":
            sys.exit(1)
        elif result["status"] == "no_integrations":
            print("No action needed.")
        elif result["status"] == "no_duplicates":
            print("No action needed.")
        elif result["status"] == "dry_run" and result["to_remove"]:
            print("\nTo execute the cleanup, run:")
            print(f"python scripts/cleanup_duplicate_slack_integrations.py --tenant-id {tenant_id} --execute")


if __name__ == "__main__":
    asyncio.run(main())
