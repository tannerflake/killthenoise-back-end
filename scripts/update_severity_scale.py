#!/usr/bin/env python3
"""Update existing severity values to new 0-100 scale."""

import asyncio
import os
import sys

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import text
from app.db import engine


async def update_severity_scale():
    """Update existing severity values from 1-5 scale to 0-100 scale."""
    print("🔄 Updating severity scale from 1-5 to 0-100...")
    
    async with engine.begin() as conn:
        # Update severity values: 1->20, 2->40, 3->60, 4->80, 5->100
        update_query = text("""
            UPDATE issues 
            SET severity = CASE 
                WHEN severity = 1 THEN 20
                WHEN severity = 2 THEN 40
                WHEN severity = 3 THEN 60
                WHEN severity = 4 THEN 80
                WHEN severity = 5 THEN 100
                ELSE severity
            END
            WHERE severity <= 5
        """)
        
        result = await conn.execute(update_query)
        
        # Get count of updated rows
        count_query = text("SELECT COUNT(*) FROM issues WHERE severity > 5")
        count_result = await conn.execute(count_query)
        updated_count = count_result.scalar()
        
        print(f"✅ Updated {updated_count} issues to new 0-100 severity scale")
        print("   - 1 → 20 (Minimal)")
        print("   - 2 → 40 (Low)")
        print("   - 3 → 60 (Medium)")
        print("   - 4 → 80 (High)")
        print("   - 5 → 100 (Critical)")
        print("\n🎉 Severity scale update complete!")


if __name__ == "__main__":
    asyncio.run(update_severity_scale())
