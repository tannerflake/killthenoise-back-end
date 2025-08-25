#!/usr/bin/env python3
"""Test script for teams API."""

import asyncio
import httpx
import json


async def test_teams_api():
    """Test the teams API endpoints."""
    base_url = "http://localhost:8000"
    tenant_id = "123e4567-e89b-12d3-a456-426614174000"
    
    print("🧪 Testing Teams API")
    print("=" * 50)
    
    async with httpx.AsyncClient() as client:
        # Test 1: Get teams
        print("\n📋 Test 1: Get teams")
        response = await client.get(f"{base_url}/api/teams/{tenant_id}")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
        else:
            print(f"Error: {response.text}")
        
        # Test 2: Create team
        print("\n📝 Test 2: Create team")
        team_data = {
            "name": "Frontend Team",
            "description": "Handles all frontend and UI issues",
            "assignment_criteria": "frontend ui react javascript typescript css html",
            "is_default_team": True
        }
        
        response = await client.post(
            f"{base_url}/api/teams/{tenant_id}",
            json=team_data
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
        else:
            print(f"Error: {response.text}")
        
        # Test 3: Get teams again
        print("\n📋 Test 3: Get teams (after creation)")
        response = await client.get(f"{base_url}/api/teams/{tenant_id}")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
        else:
            print(f"Error: {response.text}")


if __name__ == "__main__":
    asyncio.run(test_teams_api())
