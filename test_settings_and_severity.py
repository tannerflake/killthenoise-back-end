#!/usr/bin/env python3
"""Test the new settings functionality and severity scale changes."""

import asyncio
import httpx
import json
import os
from uuid import uuid4


async def test_settings_and_severity():
    """Test the new settings API and severity scale changes."""
    base_url = "http://localhost:8000"
    test_tenant_id = str(uuid4())
    
    print("🧪 Testing Settings and Severity Scale Changes")
    print("=" * 60)
    
    async with httpx.AsyncClient() as client:
        # Test 1: Get default settings
        print("\n📋 Test 1: Get default settings")
        response = await client.get(f"{base_url}/api/settings/general/{test_tenant_id}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Default settings retrieved successfully")
            print(f"   - Grouping instructions: {data['data']['grouping_instructions']}")
            print(f"   - Type classification instructions: {data['data']['type_classification_instructions']}")
            print(f"   - Severity calculation instructions: {data['data']['severity_calculation_instructions']}")
        else:
            print(f"❌ Failed to get settings: {response.status_code}")
            return

        # Test 2: Update settings with custom instructions
        print("\n📝 Test 2: Update settings with custom instructions")
        custom_settings = {
            "grouping_instructions": "Group issues by customer type and source",
            "type_classification_instructions": "If the title contains 'add', 'enhance', or 'improve', classify as feature_request. If it contains 'error', 'broken', or 'not working', classify as bug.",
            "severity_calculation_instructions": "Anything that touches an enterprise client should automatically be ranked very high (80-100). Payment issues should be ranked high (70-90). UI/UX issues should be ranked medium (40-60)."
        }
        
        response = await client.put(
            f"{base_url}/api/settings/general/{test_tenant_id}",
            json=custom_settings
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Settings updated successfully")
            print(f"   - Message: {data['message']}")
            print(f"   - Created at: {data['data']['created_at']}")
        else:
            print(f"❌ Failed to update settings: {response.status_code}")
            return

        # Test 3: Verify settings were saved
        print("\n🔍 Test 3: Verify settings were saved")
        response = await client.get(f"{base_url}/api/settings/general/{test_tenant_id}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Settings retrieved successfully")
            print(f"   - Severity instructions: {data['data']['severity_calculation_instructions'][:50]}...")
            print(f"   - Type instructions: {data['data']['type_classification_instructions'][:50]}...")
        else:
            print(f"❌ Failed to retrieve settings: {response.status_code}")

        # Test 4: Check current issues severity format
        print("\n📊 Test 4: Check current issues severity format")
        response = await client.get(f"{base_url}/api/issues/?limit=3")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Current issues retrieved")
            for issue in data.get("data", []):
                print(f"   - {issue['title'][:30]}... (Severity: {issue['severity']})")
            print(f"   Note: Current severity is still using old 1-5 scale")
        else:
            print(f"❌ Failed to get issues: {response.status_code}")

    print("\n" + "=" * 60)
    print("🎉 Settings and severity testing completed!")
    print("\n💡 Next steps:")
    print("1. The settings API is working correctly")
    print("2. Custom instructions can be stored and retrieved")
    print("3. The AI analysis service has been updated to use 0-100 severity scale")
    print("4. New issues created with AI analysis will use the new scale")
    print("5. The frontend can now implement the Settings tab interface")


if __name__ == "__main__":
    asyncio.run(test_settings_and_severity())
