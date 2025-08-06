#!/usr/bin/env python3
"""
Test script for Jira API token integration.
This demonstrates how to create a Jira integration using an API token.
"""

import asyncio
import httpx
import json
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:8000"
TENANT_ID = "550e8400-e29b-41d4-a716-446655440000"

# Replace these with your actual Jira API token and base URL
JIRA_API_TOKEN = "your_jira_api_token_here"  # Get this from Jira > Settings > Personal Access Tokens
JIRA_BASE_URL = "https://killthenoise.atlassian.net"  # Your Jira instance URL

async def test_create_jira_integration_with_api_token():
    """Test creating a Jira integration using an API token."""
    
    print("🔧 Testing Jira API Token Integration")
    print("=" * 50)
    
    # Step 1: Create integration with API token
    print("\n1️⃣ Creating Jira integration with API token...")
    
    integration_data = {
        "access_token": JIRA_API_TOKEN,
        "base_url": JIRA_BASE_URL
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/jira/integrations/{TENANT_ID}",
            json=integration_data
        )
        
        if response.status_code == 200:
            result = response.json()
            integration_id = result.get("integration_id")
            print(f"✅ Integration created successfully!")
            print(f"   Integration ID: {integration_id}")
            print(f"   Tenant ID: {result.get('tenant_id')}")
            print(f"   Message: {result.get('message')}")
            
            # Step 2: Test the connection
            print(f"\n2️⃣ Testing connection for integration {integration_id}...")
            
            status_response = await client.get(
                f"{BASE_URL}/api/jira/status/{TENANT_ID}/{integration_id}"
            )
            
            if status_response.status_code == 200:
                status_result = status_response.json()
                print(f"✅ Connection test result:")
                print(f"   Connected: {status_result.get('connected')}")
                if status_result.get('user'):
                    print(f"   User: {status_result.get('user')}")
                if status_result.get('base_url'):
                    print(f"   Base URL: {status_result.get('base_url')}")
                if status_result.get('method'):
                    print(f"   Method: {status_result.get('method')}")
            else:
                print(f"❌ Connection test failed: {status_response.text}")
            
            # Step 3: List issues
            print(f"\n3️⃣ Listing Jira issues...")
            
            issues_response = await client.get(
                f"{BASE_URL}/api/jira/issues/{TENANT_ID}/{integration_id}"
            )
            
            if issues_response.status_code == 200:
                issues_result = issues_response.json()
                if issues_result.get("success"):
                    issues = issues_result.get("issues", [])
                    total = issues_result.get("total", 0)
                    print(f"✅ Found {total} issues")
                    
                    for i, issue in enumerate(issues[:5]):  # Show first 5 issues
                        print(f"   {i+1}. {issue.get('id')} - {issue.get('summary')}")
                        print(f"      Status: {issue.get('status')}, Type: {issue.get('issue_type')}")
                    
                    if len(issues) > 5:
                        print(f"   ... and {len(issues) - 5} more issues")
                else:
                    print(f"❌ Failed to list issues: {issues_result.get('error')}")
            else:
                print(f"❌ Issues request failed: {issues_response.text}")
                
        else:
            print(f"❌ Failed to create integration: {response.text}")

async def test_list_all_integrations():
    """Test listing all Jira integrations for the tenant."""
    
    print("\n📋 Listing all Jira integrations...")
    print("=" * 50)
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/api/jira/integrations/{TENANT_ID}")
        
        if response.status_code == 200:
            result = response.json()
            integrations = result.get("integrations", [])
            
            print(f"Found {len(integrations)} integrations:")
            
            for i, integration in enumerate(integrations):
                print(f"\n{i+1}. Integration ID: {integration.get('id')}")
                print(f"   Active: {integration.get('is_active')}")
                print(f"   Created: {integration.get('created_at')}")
                
                connection_status = integration.get('connection_status', {})
                print(f"   Connected: {connection_status.get('connected')}")
                
                if connection_status.get('error'):
                    print(f"   Error: {connection_status.get('error')}")
                elif connection_status.get('user'):
                    print(f"   User: {connection_status.get('user')}")
        else:
            print(f"❌ Failed to list integrations: {response.text}")

def print_instructions():
    """Print instructions for setting up the test."""
    
    print("🚀 Jira API Token Integration Test")
    print("=" * 50)
    print()
    print("To run this test, you need to:")
    print()
    print("1️⃣ Get a Jira API Token:")
    print("   - Go to https://id.atlassian.com/manage-profile/security/api-tokens")
    print("   - Click 'Create API token'")
    print("   - Give it a name (e.g., 'KillTheNoise Integration')")
    print("   - Copy the token")
    print()
    print("2️⃣ Update the script:")
    print("   - Replace 'your_jira_api_token_here' with your actual token")
    print("   - Verify the JIRA_BASE_URL is correct")
    print()
    print("3️⃣ Run the test:")
    print("   python scripts/test_jira_api_token.py")
    print()

async def main():
    """Main test function."""
    
    print_instructions()
    
    # Check if the API token is set
    if JIRA_API_TOKEN == "your_jira_api_token_here":
        print("❌ Please update the JIRA_API_TOKEN in the script first!")
        return
    
    # Run the tests
    await test_create_jira_integration_with_api_token()
    await test_list_all_integrations()

if __name__ == "__main__":
    asyncio.run(main()) 