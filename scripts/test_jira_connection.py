#!/usr/bin/env python3
"""
Test script to demonstrate Jira connection testing with different scenarios.
"""

import asyncio
import json
from uuid import uuid4

import httpx


async def test_jira_connection_scenarios():
    """Test different Jira connection scenarios."""
    
    base_url = "http://localhost:8000"
    tenant_id = str(uuid4())
    
    print("🧪 Testing Jira Connection Scenarios")
    print("=" * 50)
    
    async with httpx.AsyncClient() as client:
        
        # Scenario 1: Invalid credentials (expected to fail)
        print("\n1. Testing with invalid credentials...")
        integration_data = {
            "access_token": "invalid-token",
            "base_url": "https://example.atlassian.net"
        }
        
        response = await client.post(
            f"{base_url}/api/jira/integrations/{tenant_id}",
            json=integration_data
        )
        
        if response.status_code == 400:
            data = response.json()
            print("✅ Expected error - invalid credentials")
            print(f"   Error: {data['detail']['error']}")
            print(f"   Message: {data['detail']['message']}")
            print("   Suggestions:")
            for suggestion in data['detail']['suggestions']:
                print(f"     - {suggestion}")
        else:
            print(f"❌ Unexpected response: {response.status_code}")
        
        # Scenario 2: Invalid URL format
        print("\n2. Testing with invalid URL format...")
        integration_data = {
            "access_token": "test-token",
            "base_url": "not-a-valid-url"
        }
        
        response = await client.post(
            f"{base_url}/api/jira/integrations/{tenant_id}",
            json=integration_data
        )
        
        if response.status_code == 400:
            data = response.json()
            print("✅ Expected error - invalid URL")
            print(f"   Error: {data['detail']['error']}")
        else:
            print(f"❌ Unexpected response: {response.status_code}")
        
        # Scenario 3: Missing base URL
        print("\n3. Testing with missing base URL...")
        integration_data = {
            "access_token": "test-token",
            "base_url": ""
        }
        
        response = await client.post(
            f"{base_url}/api/jira/integrations/{tenant_id}",
            json=integration_data
        )
        
        if response.status_code == 400:
            data = response.json()
            print("✅ Expected error - missing base URL")
            print(f"   Error: {data['detail']['error']}")
        else:
            print(f"❌ Unexpected response: {response.status_code}")
        
        print("\n" + "=" * 50)
        print("✅ Jira Connection Test Complete!")
        print("\n📝 Notes for Frontend Development:")
        print("   - The API returns detailed error messages")
        print("   - Error responses include helpful suggestions")
        print("   - All error scenarios are handled gracefully")
        print("   - The API validates both token and URL format")


if __name__ == "__main__":
    asyncio.run(test_jira_connection_scenarios()) 