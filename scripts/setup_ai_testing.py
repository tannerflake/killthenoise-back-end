#!/usr/bin/env python3
"""
Setup Script for AI-Powered Dashboard Testing

This script helps you set up the environment for testing the dashboard integration
with AI-generated issues in HubSpot and Jira.
"""

import os
import sys
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # Fallback: manually load .env file
    env_file = Path(".env")
    if env_file.exists():
        with open(env_file, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key] = value

def check_environment():
    """Check if required environment variables are set."""
    print("🔍 Checking environment configuration...")
    
    required_vars = {
        "CLAUDE_API_KEY": "Claude API key for AI issue generation",
        "DATABASE_URL": "Database connection string",
    }
    
    optional_vars = {
        "HUBSPOT_CLIENT_ID": "HubSpot OAuth client ID (optional)",
        "HUBSPOT_CLIENT_SECRET": "HubSpot OAuth client secret (optional)",
        "JIRA_CLIENT_ID": "Jira OAuth client ID (optional)",
        "JIRA_CLIENT_SECRET": "Jira OAuth client secret (optional)",
    }
    
    missing_required = []
    missing_optional = []
    
    for var, description in required_vars.items():
        if not os.getenv(var):
            missing_required.append((var, description))
        else:
            print(f"✅ {var}: Set")
    
    for var, description in optional_vars.items():
        if not os.getenv(var):
            missing_optional.append((var, description))
        else:
            print(f"✅ {var}: Set")
    
    if missing_required:
        print("\n❌ Missing required environment variables:")
        for var, description in missing_required:
            print(f"   {var}: {description}")
        return False
    
    if missing_optional:
        print("\n⚠️  Missing optional environment variables:")
        for var, description in missing_optional:
            print(f"   {var}: {description}")
        print("   (These are optional but may be needed for full testing)")
    
    return True

def check_dependencies():
    """Check if required Python packages are installed."""
    print("\n📦 Checking Python dependencies...")
    
    required_packages = [
        "fastapi",
        "uvicorn",
        "sqlalchemy",
        "asyncpg",
        "httpx",
        "anthropic",
        "pydantic"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}: Installed")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package}: Missing")
    
    if missing_packages:
        print(f"\n❌ Missing packages: {', '.join(missing_packages)}")
        print("Install with: pip install " + " ".join(missing_packages))
        return False
    
    return True

def check_database():
    """Check database connectivity."""
    print("\n🗄️  Checking database connectivity...")
    
    try:
        from app.db import get_db
        import asyncio
        
        async def test_db():
            async for session in get_db():
                from sqlalchemy import text
                await session.execute(text("SELECT 1"))
                print("✅ Database connection: Working")
                break
        
        asyncio.run(test_db())
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("Make sure your DATABASE_URL is correct and the database is running")
        return False

def create_env_template():
    """Create a template .env file if it doesn't exist."""
    env_file = Path(".env")
    
    if env_file.exists():
        print("\n✅ .env file already exists")
        return
    
    print("\n📝 Creating .env template...")
    
    template = """# KillTheNoise Backend Environment Configuration

# Database
DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/killthenoise

# AI Services
CLAUDE_API_KEY=your_claude_api_key_here

# HubSpot OAuth (Optional)
HUBSPOT_CLIENT_ID=your_hubspot_client_id
HUBSPOT_CLIENT_SECRET=your_hubspot_client_secret

# Jira OAuth (Optional)
JIRA_CLIENT_ID=your_jira_client_id
JIRA_CLIENT_SECRET=your_jira_client_secret

# Security
SECRET_KEY=your_secret_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Logging
LOG_LEVEL=INFO
"""
    
    with open(env_file, "w") as f:
        f.write(template)
    
    print("✅ Created .env template")
    print("📝 Please edit .env with your actual values")

def show_next_steps():
    """Show next steps for testing."""
    print("\n" + "=" * 60)
    print("🎯 NEXT STEPS FOR TESTING")
    print("=" * 60)
    
    print("\n1. 🔧 Configure Integrations:")
    print("   - Set up HubSpot OAuth integration")
    print("   - Set up Jira OAuth or API token integration")
    print("   - Ensure integrations are active in the database")
    
    print("\n2. 🚀 Start the API Server:")
    print("   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
    
    print("\n3. 🤖 Generate Test Issues:")
    print("   python scripts/generate_ai_test_issues.py")
    print("   - This will create realistic issues in HubSpot and Jira")
    print("   - Uses AI to generate varied, realistic content")
    
    print("\n4. 🧪 Test Dashboard Integration:")
    print("   python scripts/test_dashboard_integration.py")
    print("   - Tests the full pipeline from sync to dashboard")
    print("   - Verifies AI clustering and analytics")
    
    print("\n5. 📊 View Dashboard:")
    print("   - Check your frontend dashboard")
    print("   - Verify issues appear from both sources")
    print("   - Test AI clustering and analysis features")
    
    print("\n📚 Useful Commands:")
    print("   # Check database migrations")
    print("   alembic upgrade head")
    print("   ")
    print("   # Run existing test issues")
    print("   python scripts/create_test_issues.py")
    print("   ")
    print("   # Test individual integrations")
    print("   python scripts/test_hubspot_integration.py")
    print("   python scripts/test_jira_integration.py")

def main():
    """Main setup function."""
    print("🚀 KillTheNoise Dashboard Testing Setup")
    print("=" * 50)
    
    # Check environment
    if not check_environment():
        print("\n❌ Environment setup incomplete")
        create_env_template()
        return
    
    # Check dependencies
    if not check_dependencies():
        print("\n❌ Dependencies missing")
        return
    
    # Check database
    if not check_database():
        print("\n❌ Database setup incomplete")
        return
    
    print("\n✅ Environment setup complete!")
    
    # Show next steps
    show_next_steps()

if __name__ == "__main__":
    main()
