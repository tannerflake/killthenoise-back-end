#!/usr/bin/env python3
"""
Test script for Jira integration functionality.
This script demonstrates how to create and use Jira integrations.
"""

import asyncio
import json
import os
import sys
from typing import Dict, Any
from uuid import uuid4

import httpx


# Configuration
BASE_URL = "http://localhost:8000"
TENANT_ID = str(uuid4())  # Generate a test tenant ID


async def test_jira_integration():
    """Test the Jira integration functionality."""
    
    print("🧪 Testing Jira Integration")
    print("=" * 50)
    
    async with httpx.AsyncClient() as client:
        
        # 1. List existing integrations
        print("\n1. Listing existing Jira integrations...")
        response = await client.get(f"{BASE_URL}/api/jira/integrations/{TENANT_ID}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Found {data['total_count']} integrations")
        else:
            print(f"❌ Failed to list integrations: {response.status_code}")
            return
        
        # 2. Create a test integration (this will fail with invalid credentials, but shows the flow)
        print("\n2. Creating a test Jira integration...")
        integration_data = {
            "access_token": "test-token",
            "base_url": "https://example.atlassian.net"
        }
        
        response = await client.post(
            f"{BASE_URL}/api/jira/integrations/{TENANT_ID}",
            json=integration_data
        )
        
        if response.status_code == 400:
            print("✅ Expected error - invalid credentials (this is correct behavior)")
            print(f"   Error: {response.json()['detail']}")
        else:
            print(f"❌ Unexpected response: {response.status_code}")
            return
        
        # 3. Test connection endpoint (with invalid integration)
        print("\n3. Testing connection endpoint...")
        test_integration_id = str(uuid4())
        response = await client.get(f"{BASE_URL}/api/jira/status/{TENANT_ID}/{test_integration_id}")
        
        if response.status_code == 200:
            data = response.json()
            if not data.get("connected", True):
                print("✅ Expected error - integration not found (this is correct behavior)")
                print(f"   Error: {data.get('error', 'Unknown error')}")
            else:
                print(f"❌ Unexpected response: {response.status_code}")
        else:
            print(f"❌ Unexpected response: {response.status_code}")
        
        # 4. Test issues endpoint (with invalid integration)
        print("\n4. Testing issues endpoint...")
        response = await client.get(f"{BASE_URL}/api/jira/issues/{TENANT_ID}/{test_integration_id}")
        
        if response.status_code == 200:
            data = response.json()
            if not data.get("success", True):
                print("✅ Expected error - integration not found (this is correct behavior)")
                print(f"   Error: {data.get('error', 'Unknown error')}")
            else:
                print(f"❌ Unexpected response: {response.status_code}")
        else:
            print(f"❌ Unexpected response: {response.status_code}")
        
        # 5. Test projects endpoint (with invalid integration)
        print("\n5. Testing projects endpoint...")
        response = await client.get(f"{BASE_URL}/api/jira/projects/{TENANT_ID}/{test_integration_id}")
        
        if response.status_code == 200:
            data = response.json()
            if not data.get("success", True):
                print("✅ Expected error - integration not found (this is correct behavior)")
                print(f"   Error: {data.get('error', 'Unknown error')}")
            else:
                print(f"❌ Unexpected response: {response.status_code}")
        else:
            print(f"❌ Unexpected response: {response.status_code}")
        
        # 6. Test sync endpoint (with invalid integration)
        print("\n6. Testing sync endpoint...")
        response = await client.post(f"{BASE_URL}/api/jira/sync/{TENANT_ID}/{test_integration_id}")
        
        if response.status_code == 200:
            data = response.json()
            if not data.get("success", True):
                print("✅ Expected error - integration not found (this is correct behavior)")
                print(f"   Error: {data.get('error', 'Unknown error')}")
            else:
                print(f"❌ Unexpected response: {response.status_code}")
        else:
            print(f"❌ Unexpected response: {response.status_code}")
        
        print("\n" + "=" * 50)
        print("✅ Jira Integration Test Complete!")
        print("\n📋 Available Jira API Endpoints:")
        print("   GET  /api/jira/integrations/{tenant_id}")
        print("   POST /api/jira/integrations/{tenant_id}")
        print("   GET  /api/jira/status/{tenant_id}/{integration_id}")
        print("   GET  /api/jira/issues/{tenant_id}/{integration_id}")
        print("   GET  /api/jira/issues/{tenant_id}/{integration_id}/{issue_key}")
        print("   POST /api/jira/issues/{tenant_id}/{integration_id}")
        print("   PUT  /api/jira/issues/{tenant_id}/{integration_id}/{issue_key}")
        print("   GET  /api/jira/projects/{tenant_id}/{integration_id}")
        print("   POST /api/jira/sync/{tenant_id}/{integration_id}")
        print("\n🔗 API Documentation: http://localhost:8000/docs")


if __name__ == "__main__":
    asyncio.run(test_jira_integration()) 