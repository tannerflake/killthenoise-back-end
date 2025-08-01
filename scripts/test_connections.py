#!/usr/bin/env python3
"""
Standalone script to test all external service connections.
Run this script to verify that all environment variables are properly configured
and all external services are accessible.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from app.services.connection_service import ConnectionService


async def main():
    """Test all external service connections."""
    print("🔍 Testing external service connections...")
    print("=" * 50)
    
    # Check if required environment variables are set
    required_vars = [
        "HUBSPOT_CLIENT_ID", 
        "HUBSPOT_CLIENT_SECRET",
        "HUBSPOT_REDIRECT_URI",
        "CLAUDE_API_KEY",
        "SUPABASE_URL",
        "SUPABASE_SERVICE_ROLE_KEY"
    ]
    
    print("📋 Environment Variables Check:")
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            if "KEY" in var or "SECRET" in var or "PASSWORD" in var:
                masked_value = value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
                print(f"  ✅ {var}: {masked_value}")
            else:
                print(f"  ✅ {var}: {value}")
        else:
            print(f"  ❌ {var}: NOT SET")
            missing_vars.append(var)
    
    if missing_vars:
        print(f"\n⚠️  Missing environment variables: {', '.join(missing_vars)}")
        print("Please set these variables in your .env file before testing connections.")
        return
    
    print("\n🚀 Testing Service Connections:")
    print("-" * 30)
    
    # Create connection service
    connection_service = ConnectionService()
    
    # Test all connections
    results = await connection_service.test_all_connections()
    summary = connection_service.get_connection_summary(results)
    
    # Display results
    for result in results:
        status = "✅" if result.success else "❌"
        print(f"{status} {result.service}: {result.response_time:.3f}s")
        if not result.success and result.error:
            print(f"    Error: {result.error}")
    
    print("\n📊 Summary:")
    print(f"  Total Tests: {summary['total_tests']}")
    print(f"  Successful: {summary['successful_tests']}")
    print(f"  Failed: {summary['failed_tests']}")
    print(f"  Success Rate: {summary['success_rate']:.1f}%")
    print(f"  Average Response Time: {summary['average_response_time']:.3f}s")
    
    if summary['success_rate'] == 100:
        print("\n🎉 All connections successful!")
        return 0
    else:
        print(f"\n⚠️  {summary['failed_tests']} connection(s) failed. Please check your configuration.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 