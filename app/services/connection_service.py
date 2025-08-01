from __future__ import annotations

import os
import time
from typing import Dict, List, Optional
from uuid import UUID

import httpx
from anthropic import Anthropic
from supabase import Client, create_client


class ConnectionTestResult:
    """Result of a connection test."""
    
    def __init__(self, service: str, success: bool, response_time: float, error: Optional[str] = None):
        self.service = service
        self.success = success
        self.response_time = response_time
        self.error = error
    
    def to_dict(self) -> Dict[str, any]:
        return {
            "service": self.service,
            "success": self.success,
            "response_time": self.response_time,
            "error": self.error
        }


class ConnectionService:
    """Service for testing connections to all external services."""
    
    def __init__(self):
        self.hubspot_client_id = os.getenv("HUBSPOT_CLIENT_ID")
        self.hubspot_client_secret = os.getenv("HUBSPOT_CLIENT_SECRET")
        self.hubspot_redirect_uri = os.getenv("HUBSPOT_REDIRECT_URI")
        self.claude_api_key = os.getenv("CLAUDE_API_KEY")
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    

    
    async def test_hubspot_connection(self) -> ConnectionTestResult:
        """Test HubSpot API connection."""
        start_time = time.time()
        try:
            # Test HubSpot OAuth endpoint
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    "https://api.hubapi.com/oauth/v1/authorize",
                    params={
                        "client_id": self.hubspot_client_id,
                        "redirect_uri": self.hubspot_redirect_uri,
                        "scope": "contacts"
                    }
                )
                response_time = time.time() - start_time
                return ConnectionTestResult("HubSpot", True, response_time)
        except Exception as e:
            response_time = time.time() - start_time
            return ConnectionTestResult("HubSpot", False, response_time, str(e))
    
    async def test_claude_connection(self) -> ConnectionTestResult:
        """Test Claude API connection."""
        start_time = time.time()
        try:
            if not self.claude_api_key:
                raise ValueError("Claude API key not configured")
            
            anthropic = Anthropic(api_key=self.claude_api_key)
            # Test with a simple message using a valid model
            response = anthropic.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=10,
                messages=[{"role": "user", "content": "Hello"}]
            )
            response_time = time.time() - start_time
            return ConnectionTestResult("Claude API", True, response_time)
        except Exception as e:
            response_time = time.time() - start_time
            return ConnectionTestResult("Claude API", False, response_time, str(e))
    
    async def test_supabase_connection(self) -> ConnectionTestResult:
        """Test Supabase connection."""
        start_time = time.time()
        try:
            if not self.supabase_url or not self.supabase_service_role_key:
                raise ValueError("Supabase URL or service role key not configured")
            
            supabase: Client = create_client(self.supabase_url, self.supabase_service_role_key)
            # Test connection by making a simple request to the API
            response = supabase.auth.get_user()
            response_time = time.time() - start_time
            return ConnectionTestResult("Supabase", True, response_time)
        except Exception as e:
            response_time = time.time() - start_time
            return ConnectionTestResult("Supabase", False, response_time, str(e))
    
    async def test_all_connections(self) -> List[ConnectionTestResult]:
        """Test all external service connections."""
        results = []
        
        # Test all connections concurrently
        tasks = [
            self.test_hubspot_connection(),
            self.test_claude_connection(),
            self.test_supabase_connection()
        ]
        
        for task in tasks:
            result = await task
            results.append(result)
        
        return results
    
    def get_connection_summary(self, results: List[ConnectionTestResult]) -> Dict[str, any]:
        """Get a summary of all connection test results."""
        total_tests = len(results)
        successful_tests = sum(1 for r in results if r.success)
        failed_tests = total_tests - successful_tests
        
        avg_response_time = sum(r.response_time for r in results) / total_tests if total_tests > 0 else 0
        
        return {
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "failed_tests": failed_tests,
            "success_rate": (successful_tests / total_tests * 100) if total_tests > 0 else 0,
            "average_response_time": avg_response_time,
            "results": [r.to_dict() for r in results]
        }


# Factory function for dependency injection
def create_connection_service() -> ConnectionService:
    """Create a connection service instance."""
    return ConnectionService() 