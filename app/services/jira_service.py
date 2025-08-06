from __future__ import annotations

import os
from typing import Dict, List, Any, Optional
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant_integration import TenantIntegration


class JiraService:
    """Service for interacting with Jira API."""
    
    def __init__(self, tenant_id: UUID, integration_id: UUID, session: AsyncSession):
        self.tenant_id = tenant_id
        self.integration_id = integration_id
        self.session = session
        self._access_token: Optional[str] = None
        self._base_url: Optional[str] = None
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        await self._load_integration()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
    
    async def _load_integration(self) -> None:
        """Load integration configuration from database."""
        print(f"[DEBUG] Loading integration: {self.integration_id}")
        integration = await self.session.get(TenantIntegration, self.integration_id)
        print(f"[DEBUG] Found integration: {integration is not None}")
        
        if not integration or integration.tenant_id != self.tenant_id:
            print(f"[DEBUG] Integration not found or tenant mismatch")
            raise ValueError(f"Integration {self.integration_id} not found for tenant {self.tenant_id}")
        
        print(f"[DEBUG] Integration is_active: {integration.is_active}")
        if not integration.is_active:
            raise ValueError(f"Integration {self.integration_id} is not active")
        
        config = integration.config or {}
        print(f"[DEBUG] Loading integration config: {config}")
        self._access_token = config.get("access_token")
        self._base_url = config.get("base_url")
        self._refresh_token = config.get("refresh_token")
        self._email = config.get("email")  # Add email for Basic Auth
        
        print(f"[DEBUG] Access token: {self._access_token[:20] if self._access_token else 'None'}...")
        print(f"[DEBUG] Base URL: {self._base_url}")
        print(f"[DEBUG] Email: {self._email}")
        print(f"[DEBUG] Refresh token: {self._refresh_token[:20] if self._refresh_token else 'None'}...")
        
        if not self._access_token:
            raise ValueError("No access token configured for Jira integration")
        
        if not self._base_url:
            raise ValueError("No base URL configured for Jira integration")
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if not self._client:
            # For API tokens, we use Basic Auth with email:token
            # For OAuth tokens, we use Bearer auth
            if self._access_token.startswith('ATATT'):
                # API token - use Basic Auth
                if self._email:
                    import base64
                    credentials = base64.b64encode(f"{self._email}:{self._access_token}".encode()).decode()
                    auth_header = f"Basic {credentials}"
                else:
                    # Fallback to Bearer if no email
                    auth_header = f"Bearer {self._access_token}"
            else:
                # OAuth token
                auth_header = f"Bearer {self._access_token}"
            
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers={
                    "Authorization": auth_header,
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                }
            )
        return self._client
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test the Jira connection."""
        try:
            # Load integration configuration first
            await self._load_integration()
            
            # Check if we have the required configuration
            if not self._access_token or not self._base_url:
                return {
                    "connected": False,
                    "error": "Integration not properly configured - missing access token or base URL"
                }
            
            # Test connection based on token type
            client = await self._get_client()
            
            if self._access_token.startswith('ATATT'):
                # API token - test with Jira instance API
                try:
                    response = await client.get(f"{self._base_url}/rest/api/3/myself")
                    response.raise_for_status()
                    user_data = response.json()
                    return {
                        "connected": True,
                        "user": {
                            "account_id": user_data.get("accountId"),
                            "display_name": user_data.get("displayName"),
                            "email": user_data.get("emailAddress")
                        },
                        "base_url": self._base_url,
                        "method": "api_token"
                    }
                except Exception as e:
                    return {
                        "connected": False,
                        "error": f"API token test failed: {str(e)}"
                    }
            else:
                # OAuth token - test with Atlassian Cloud API
                try:
                    response = await client.get("https://api.atlassian.com/oauth/token/accessible-resources")
                    response.raise_for_status()
                    resources = response.json()
                    
                    # Check if our base_url is in the accessible resources
                    base_url_found = any(resource.get("url") == self._base_url for resource in resources)
                    
                    if base_url_found:
                        return {
                            "connected": True,
                            "user": {
                                "account_id": "oauth_user",
                                "display_name": "OAuth User",
                                "email": "oauth@example.com"
                            },
                            "base_url": self._base_url,
                            "method": "oauth"
                        }
                    else:
                        return {
                            "connected": False,
                            "error": "Jira instance not found in accessible resources"
                        }
                except Exception as e:
                    return {
                        "connected": False,
                        "error": f"OAuth test failed: {str(e)}"
                    }
                    
        except Exception as e:
            return {
                "connected": False,
                "error": str(e)
            }
    
    async def list_issues(self, limit: Optional[int] = None, jql: Optional[str] = None) -> Dict[str, Any]:
        """List Jira issues."""
        try:
            # Load integration configuration first
            await self._load_integration()
            
            # Check if we have the required configuration
            if not self._access_token or not self._base_url:
                return {
                    "success": False,
                    "error": "Integration not properly configured - missing access token or base URL",
                    "issues": []
                }
            
            client = await self._get_client()
            
            # Build JQL query
            if jql:
                query = jql
            else:
                query = "ORDER BY updated DESC"
            
            params = {
                "jql": query,
                "maxResults": limit or 50,
                "fields": "summary,status,priority,assignee,updated,created,issuetype,project"
            }
            
            response = await client.get(f"{self._base_url}/rest/api/3/search", params=params)
            response.raise_for_status()
            
            data = response.json()
            issues = []
            
            # Add null check for data
            if not data:
                return {
                    "success": False,
                    "error": "Invalid response from Jira API",
                    "issues": []
                }
            
            for issue in data.get("issues", []):
                if not issue:
                    continue
                    
                fields = issue.get("fields", {})
                if not fields:
                    continue
                    
                # Safe navigation for nested objects
                status_obj = fields.get("status", {})
                priority_obj = fields.get("priority", {})
                assignee_obj = fields.get("assignee", {})
                issuetype_obj = fields.get("issuetype", {})
                project_obj = fields.get("project", {})
                
                issue_data = {
                    "id": issue.get("key"),
                    "summary": fields.get("summary"),
                    "status": status_obj.get("name") if status_obj else None,
                    "priority": priority_obj.get("name") if priority_obj else None,
                    "assignee": assignee_obj.get("displayName") if assignee_obj else None,
                    "issue_type": issuetype_obj.get("name") if issuetype_obj else None,
                    "project": project_obj.get("name") if project_obj else None,
                    "created": fields.get("created"),
                    "updated": fields.get("updated"),
                    "url": f"{self._base_url}/browse/{issue.get('key')}" if issue.get('key') else None
                }
                issues.append(issue_data)
            
            return {
                "success": True,
                "issues": issues,
                "total": data.get("total", 0),
                "max_results": data.get("maxResults", 0)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "issues": []
            }
    
    async def get_issue(self, issue_key: str) -> Dict[str, Any]:
        """Get a specific Jira issue."""
        try:
            client = await self._get_client()
            response = await client.get(f"{self._base_url}/rest/api/3/issue/{issue_key}")
            response.raise_for_status()
            
            issue = response.json()
            if not issue:
                return {
                    "success": False,
                    "error": "Invalid response from Jira API"
                }
                
            fields = issue.get("fields", {})
            if not fields:
                return {
                    "success": False,
                    "error": "No fields found in Jira issue"
                }
            
            # Safe navigation for nested objects
            status_obj = fields.get("status", {})
            priority_obj = fields.get("priority", {})
            assignee_obj = fields.get("assignee", {})
            reporter_obj = fields.get("reporter", {})
            issuetype_obj = fields.get("issuetype", {})
            project_obj = fields.get("project", {})
            
            return {
                "success": True,
                "issue": {
                    "id": issue.get("key"),
                    "summary": fields.get("summary"),
                    "description": fields.get("description"),
                    "status": status_obj.get("name") if status_obj else None,
                    "priority": priority_obj.get("name") if priority_obj else None,
                    "assignee": assignee_obj.get("displayName") if assignee_obj else None,
                    "reporter": reporter_obj.get("displayName") if reporter_obj else None,
                    "issue_type": issuetype_obj.get("name") if issuetype_obj else None,
                    "project": project_obj.get("name") if project_obj else None,
                    "created": fields.get("created"),
                    "updated": fields.get("updated"),
                    "url": f"{self._base_url}/browse/{issue.get('key')}" if issue.get('key') else None
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def create_issue(self, project_key: str, summary: str, description: str, 
                          issue_type: str = "Task") -> Dict[str, Any]:
        """Create a new Jira issue."""
        try:
            client = await self._get_client()
            
            issue_data = {
                "fields": {
                    "project": {"key": project_key},
                    "summary": summary,
                    "description": {
                        "type": "doc",
                        "version": 1,
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": description
                                    }
                                ]
                            }
                        ]
                    },
                    "issuetype": {"name": issue_type}
                }
            }
            
            response = await client.post(f"{self._base_url}/rest/api/3/issue", json=issue_data)
            response.raise_for_status()
            
            created_issue = response.json()
            return {
                "success": True,
                "issue_key": created_issue.get("key"),
                "issue_id": created_issue.get("id"),
                "url": f"{self._base_url}/browse/{created_issue.get('key')}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def update_issue(self, issue_key: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update a Jira issue."""
        try:
            client = await self._get_client()
            
            # Convert updates to Jira format
            fields = {}
            if "summary" in updates:
                fields["summary"] = updates["summary"]
            if "description" in updates:
                fields["description"] = {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": updates["description"]
                                }
                            ]
                        }
                    ]
                }
            
            if not fields:
                return {"success": False, "error": "No valid fields to update"}
            
            issue_data = {"fields": fields}
            response = await client.put(f"{self._base_url}/rest/api/3/issue/{issue_key}", json=issue_data)
            response.raise_for_status()
            
            return {"success": True}
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def list_projects(self) -> Dict[str, Any]:
        """List Jira projects."""
        try:
            client = await self._get_client()
            response = await client.get(f"{self._base_url}/rest/api/3/project")
            response.raise_for_status()
            
            projects = []
            for project in response.json():
                projects.append({
                    "key": project.get("key"),
                    "name": project.get("name"),
                    "id": project.get("id")
                })
            
            return {
                "success": True,
                "projects": projects
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "projects": []
            }
    
    async def _validate_token(self, access_token: str, base_url: str = None) -> bool:
        """Validate a Jira access token."""
        try:
            url = base_url or self._base_url
            if not url:
                return False
                
            async with httpx.AsyncClient(
                timeout=10.0,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json"
                }
            ) as client:
                response = await client.get(f"{url}/rest/api/3/myself")
                return response.status_code == 200
        except Exception:
            return False
    
    async def _refresh_token(self) -> bool:
        """Refresh the OAuth access token using the refresh token."""
        try:
            if not self._refresh_token:
                return False
            
            client_id = os.getenv("JIRA_CLIENT_ID")
            client_secret = os.getenv("JIRA_CLIENT_SECRET")
            
            if not client_id or not client_secret:
                return False
            
            token_data = {
                "grant_type": "refresh_token",
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": self._refresh_token,
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://auth.atlassian.com/oauth/token",
                    data=token_data,
                    timeout=15
                )
                response.raise_for_status()
                token_response = response.json()
            
            new_access_token = token_response.get("access_token")
            new_refresh_token = token_response.get("refresh_token")
            
            if not new_access_token:
                return False
            
            # Update the integration with new tokens
            integration = await self.session.get(TenantIntegration, self.integration_id)
            if integration:
                config = integration.config or {}
                config["access_token"] = new_access_token
                if new_refresh_token:
                    config["refresh_token"] = new_refresh_token
                
                integration.config = config
                await self.session.commit()
                
                # Update local tokens
                self._access_token = new_access_token
                if new_refresh_token:
                    self._refresh_token = new_refresh_token
                
                return True
            
            return False
            
        except Exception as e:
            print(f"[DEBUG] Token refresh failed: {e}")
            return False


def create_jira_service(tenant_id: UUID, integration_id: UUID, session: AsyncSession) -> JiraService:
    """Create a Jira service instance."""
    return JiraService(tenant_id, integration_id, session) 