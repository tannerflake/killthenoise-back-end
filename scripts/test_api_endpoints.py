#!/usr/bin/env python3
"""
Test script for health API endpoints.
This script tests the FastAPI health endpoints to verify they work correctly.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


async def test_api_endpoints():
    """Test all health API endpoints."""
    base_url = "http://localhost:8000"  # Default FastAPI port
    
    print("🔍 Testing API Health Endpoints...")
    print("=" * 50)
    
    endpoints = [
        ("/health/", "Basic Health Check"),
        ("/health/connections", "All Connections Test"),
        ("/health/connections/hubspot", "HubSpot Connection Test"),
        ("/health/connections/claude", "Claude API Connection Test"),
        ("/health/connections/supabase", "Supabase Connection Test"),
    ]
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for endpoint, description in endpoints:
            print(f"\n📡 Testing: {description}")
            print(f"   Endpoint: {endpoint}")
            
            try:
                response = await client.get(f"{base_url}{endpoint}")
                
                if response.status_code == 200:
                    print(f"   ✅ Status: {response.status_code}")
                    data = response.json()
                    
                    # Pretty print the response for better readability
                    if isinstance(data, dict):
                        if "results" in data:
                            # Connection test results
                            print(f"   📊 Success Rate: {data.get('success_rate', 0):.1f}%")
                            print(f"   ⏱️  Average Response Time: {data.get('average_response_time', 0):.3f}s")
                            print(f"   📈 Tests: {data.get('successful_tests', 0)}/{data.get('total_tests', 0)} successful")
                        else:
                            # Simple health check
                            print(f"   📄 Response: {json.dumps(data, indent=2)}")
                    else:
                        print(f"   📄 Response: {data}")
                else:
                    print(f"   ❌ Status: {response.status_code}")
                    print(f"   📄 Response: {response.text}")
                    
            except httpx.ConnectError:
                print(f"   ❌ Connection Error: Could not connect to {base_url}")
                print(f"   💡 Make sure the FastAPI server is running on {base_url}")
            except Exception as e:
                print(f"   ❌ Error: {str(e)}")
    
    print("\n" + "=" * 50)
    print("🎯 API Endpoint Testing Complete!")
    print("\n💡 To start the FastAPI server, run:")
    print("   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")


if __name__ == "__main__":
    asyncio.run(test_api_endpoints()) 