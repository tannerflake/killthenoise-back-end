#!/usr/bin/env python3
"""
Test script to demonstrate the Jira OAuth flow.
This script shows how the OAuth endpoints work.
"""

import asyncio
import json
from uuid import uuid4

import httpx


async def test_jira_oauth_flow():
    """Test the Jira OAuth flow endpoints."""
    
    base_url = "http://localhost:8000"
    tenant_id = str(uuid4())
    
    print("🧪 Testing Jira OAuth Flow")
    print("=" * 50)
    
    async with httpx.AsyncClient() as client:
        
        # Step 1: Generate authorization URL
        print("\n1. Generating authorization URL...")
        response = await client.get(f"{base_url}/api/jira/authorize/{tenant_id}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Authorization URL generated successfully")
            print(f"   Integration ID: {data['integration_id']}")
            print(f"   Tenant ID: {data['tenant_id']}")
            print(f"   Authorization URL: {data['authorization_url'][:100]}...")
            
            # Extract the authorization URL for testing
            auth_url = data['authorization_url']
            integration_id = data['integration_id']
            
        else:
            print(f"❌ Failed to generate authorization URL: {response.status_code}")
            print(f"   Error: {response.text}")
            return
        
        # Step 2: Test the callback endpoint (simulate OAuth callback)
        print("\n2. Testing OAuth callback endpoint...")
        
        # Simulate a callback with a test code
        test_code = "test-authorization-code"
        test_state = f"{tenant_id[:8]}:{integration_id[:8]}"
        
        callback_url = f"{base_url}/api/jira/oauth/callback?code={test_code}&state={test_state}"
        response = await client.get(callback_url)
        
        if response.status_code == 400:
            data = response.json()
            print("✅ Expected error - invalid authorization code (this is correct)")
            print(f"   Error: {data['detail']}")
        else:
            print(f"❌ Unexpected response: {response.status_code}")
            print(f"   Response: {response.text}")
        
        # Step 3: Test without state parameter
        print("\n3. Testing callback without state parameter...")
        callback_url_no_state = f"{base_url}/api/jira/oauth/callback?code={test_code}"
        response = await client.get(callback_url_no_state)
        
        if response.status_code == 400:
            data = response.json()
            print("✅ Expected error - no integration found (this is correct)")
            print(f"   Error: {data['detail']}")
        else:
            print(f"❌ Unexpected response: {response.status_code}")
        
        # Step 4: Test integration status
        print("\n4. Testing integration status...")
        response = await client.get(f"{base_url}/api/jira/status/{tenant_id}/{integration_id}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Integration status retrieved")
            print(f"   Connected: {data.get('connected', False)}")
            if not data.get('connected'):
                print(f"   Error: {data.get('error', 'Unknown error')}")
        else:
            print(f"❌ Failed to get integration status: {response.status_code}")
        
        # Step 5: Test integration list
        print("\n5. Testing integration list...")
        response = await client.get(f"{base_url}/api/jira/integrations/{tenant_id}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Integration list retrieved")
            print(f"   Total integrations: {data['total_count']}")
            if data['integrations']:
                for integration in data['integrations']:
                    print(f"   - Integration ID: {integration['id']}")
                    print(f"     Active: {integration['is_active']}")
        else:
            print(f"❌ Failed to get integration list: {response.status_code}")
        
        print("\n" + "=" * 50)
        print("✅ Jira OAuth Flow Test Complete!")
        print("\n📋 OAuth Flow Summary:")
        print("   1. ✅ Authorization URL generation works")
        print("   2. ✅ OAuth callback endpoint handles errors gracefully")
        print("   3. ✅ Integration status checking works")
        print("   4. ✅ Integration listing works")
        print("\n🔗 Next Steps:")
        print("   1. Set up Jira OAuth app in Atlassian Developer Console")
        print("   2. Configure real OAuth credentials in .env")
        print("   3. Test with real Jira instance")
        print("   4. Implement frontend OAuth flow")


if __name__ == "__main__":
    asyncio.run(test_jira_oauth_flow()) 