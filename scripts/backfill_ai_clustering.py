#!/usr/bin/env python3
"""Backfill existing issues into AI clustering system."""

import asyncio
import os
import sys
from uuid import uuid4

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import select
from app.db import engine
from app.models.issue import Issue
from app.services.ai_clustering_service import AIIssueClusteringService


async def backfill_ai_clustering():
    """Backfill existing issues into AI clustering system."""
    print("🔄 Backfilling existing issues into AI clustering system...")
    
    # Use a default tenant ID for backfill
    default_tenant_id = uuid4()
    
    async with engine.begin() as conn:
        # Get all existing issues
        stmt = select(Issue)
        result = await conn.execute(stmt)
        issues = result.scalars().all()
        
        if not issues:
            print("✅ No issues found to backfill.")
            return
        
        print(f"📊 Found {len(issues)} issues to backfill...")
        
        # Create AI clustering service
        clustering = AIIssueClusteringService(default_tenant_id, conn)
        
        created_count = 0
        for i, issue in enumerate(issues, 1):
            try:
                print(f"🔍 Processing issue {i}/{len(issues)}: {issue.title[:50]}...")
                
                # Create raw report from issue
                await clustering.ingest_raw_report(
                    source=issue.source,
                    external_id=str(issue.id),
                    title=issue.title,
                    body=issue.description,
                    url=None,
                    commit=False  # Bulk insert without individual commits
                )
                
                created_count += 1
                
            except Exception as e:
                print(f"   ❌ Error processing issue {issue.id}: {e}")
                continue
        
        # Commit all changes
        await conn.commit()
        
        print(f"✅ Created {created_count} raw reports")
        
        # Now run clustering to create AI issue groups
        print("🤖 Running AI clustering...")
        try:
            clustering_result = await clustering.recluster()
            print(f"✅ Clustering completed: {clustering_result}")
        except Exception as e:
            print(f"❌ Error during clustering: {e}")
        
        print("\n🎉 AI clustering backfill complete!")


if __name__ == "__main__":
    asyncio.run(backfill_ai_clustering())
