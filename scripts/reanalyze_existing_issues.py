#!/usr/bin/env python3
"""Re-analyze existing issues with the new 0-100 severity scale."""

import asyncio
import os
import sys
from typing import List, Dict, Any
from uuid import uuid4

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db, engine
from app.models.issue import Issue
from app.services.ai_analysis_service import AIAnalysisService
from app.services.ai_integration_service import AIIntegrationService
from app.services.ai_config_service import get_claude_api_key


async def reanalyze_issues():
    """Re-analyze existing issues with the new severity scale."""
    print("🔄 Re-analyzing existing issues with new 0-100 severity scale...")
    
    # Check if AI is enabled
    api_key = get_claude_api_key()
    if not api_key:
        print("❌ No Claude API key found. Set CLAUDE_API_KEY environment variable.")
        return
    
    async with engine.begin() as conn:
        # Get all issues that need re-analysis
        stmt = select(Issue).where(Issue.severity <= 5)  # Only re-analyze old scale issues
        result = await conn.execute(stmt)
        issues = result.scalars().all()
        
        if not issues:
            print("✅ No issues found that need re-analysis.")
            return
        
        print(f"📊 Found {len(issues)} issues to re-analyze...")
        
        # Use a default tenant ID for re-analysis
        default_tenant_id = uuid4()
        
        # Create AI services
        ai_analysis_service = AIAnalysisService(default_tenant_id, api_key)
        
        updated_count = 0
        for i, issue in enumerate(issues, 1):
            try:
                print(f"🔍 Analyzing issue {i}/{len(issues)}: {issue.title[:50]}...")
                
                # Prepare context for analysis
                context = {
                    "priority": "medium",
                    "customer_type": "standard",
                    "source": issue.source
                }
                
                # Perform AI analysis
                analysis = await ai_analysis_service.analyze_ticket_comprehensive(
                    issue.title, 
                    issue.description or "", 
                    context
                )
                
                # Extract new severity score
                severity_data = analysis.get("severity", {})
                new_severity = severity_data.get("severity_score", 50)
                
                # Update the issue
                issue.severity = new_severity
                
                # Also update type if AI analysis is available
                type_data = analysis.get("type", {})
                if type_data.get("confidence", 0) > 0.3:
                    issue.type = type_data.get("type", "bug")
                    issue.ai_type_confidence = type_data.get("confidence")
                    issue.ai_type_reasoning = type_data.get("reasoning")
                
                updated_count += 1
                
                print(f"   ✅ Updated severity: {new_severity}/100")
                
            except Exception as e:
                print(f"   ❌ Error analyzing issue {issue.id}: {e}")
                continue
        
        # Commit all changes
        await conn.commit()
        
        print(f"\n🎉 Re-analysis complete!")
        print(f"   - Updated {updated_count} issues")
        print(f"   - New severity scale: 0-100")
        print(f"   - Issues now ready for proper x/100 display")


if __name__ == "__main__":
    asyncio.run(reanalyze_issues())
