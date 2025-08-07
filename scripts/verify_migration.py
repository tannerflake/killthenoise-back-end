#!/usr/bin/env python3
"""Verify that the AI migration was applied successfully to Supabase."""

import asyncio
import os
from sqlalchemy import text
from app.db import engine

async def verify_ai_fields():
    """Check if AI fields were added to the issues table."""
    print("🔍 Verifying AI fields migration...")
    
    async with engine.begin() as conn:
        try:
            # Check if the issues table exists and has AI fields (PostgreSQL/Supabase)
            result = await conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'issues'
                ORDER BY ordinal_position
            """))
            columns = result.fetchall()
            column_names = [col[0] for col in columns]
            
            # AI fields that should exist
            expected_ai_fields = [
                'tenant_id',
                'ai_enabled',
                'ai_sentiment', 
                'ai_urgency',
                'ai_category',
                'ai_tags',
                'ai_severity_confidence',
                'ai_sentiment_confidence', 
                'ai_category_confidence',
                'ai_severity_reasoning'
            ]
            
            print(f"📋 Found {len(column_names)} columns in issues table:")
            for col in column_names:
                status = "✅" if col in expected_ai_fields else "📄"
                print(f"   {status} {col}")
            
            # Check which AI fields are missing
            missing_fields = [field for field in expected_ai_fields if field not in column_names]
            
            if missing_fields:
                print(f"\n❌ Missing AI fields: {missing_fields}")
                print("💡 Run 'alembic upgrade head' to apply migrations")
                return False
            else:
                print(f"\n✅ All AI fields present! Migration successful.")
                
                # Check indexes (PostgreSQL/Supabase)
                result = await conn.execute(text("""
                    SELECT indexname 
                    FROM pg_indexes 
                    WHERE tablename = 'issues'
                """))
                indexes = result.fetchall()
                print(f"\n📊 Found {len(indexes)} indexes:")
                for idx in indexes:
                    print(f"   📑 {idx[0]}")
                
                return True
                
        except Exception as e:
            print(f"❌ Error checking migration: {e}")
            return False

async def test_ai_ready():
    """Test if the system is ready for AI processing."""
    print(f"\n🤖 Testing AI readiness...")
    
    try:
        from app.services.ai_config_service import is_ai_enabled, get_claude_api_key
        
        api_key = get_claude_api_key()
        if api_key:
            print("✅ Claude API key found")
        else:
            print("⚠️  Claude API key not configured")
            print("   Set CLAUDE_API_KEY or ANTHROPIC_API_KEY environment variable")
        
        ai_enabled = is_ai_enabled()
        print(f"🔧 AI Processing: {'Enabled' if ai_enabled else 'Disabled'}")
        
        return ai_enabled
        
    except Exception as e:
        print(f"❌ AI configuration error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Verifying Database Migration & AI Setup...\n")
    
    async def main():
        migration_ok = await verify_ai_fields()
        ai_ready = await test_ai_ready()
        
        print(f"\n📋 Migration Status: {'✅ Complete' if migration_ok else '❌ Incomplete'}")
        print(f"🤖 AI Status: {'✅ Ready' if ai_ready else '⚠️  Needs Configuration'}")
        
        if migration_ok and ai_ready:
            print(f"\n🎉 System ready for AI-powered ticket processing!")
        elif migration_ok:
            print(f"\n⚙️  Database ready. Set CLAUDE_API_KEY to enable AI features.")
        else:
            print(f"\n🔧 Run 'alembic upgrade head' to complete setup.")
    
    asyncio.run(main())