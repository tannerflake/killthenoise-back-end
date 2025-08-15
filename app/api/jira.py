from __future__ import annotations

import datetime as dt
import os
from typing import Dict, List, Any, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.tenant_integration import TenantIntegration
from app.services.jira_service import create_jira_service

router = APIRouter(prefix="/api/jira", tags=["Jira"])


# -------------------------------------------------------------------------
# Multi-tenant Jira endpoints
# -------------------------------------------------------------------------

@router.get("/status/{tenant_id}/{integration_id}")
async def jira_status(
    tenant_id: UUID, 
    integration_id: UUID,
    session: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Test Jira connection status for a specific tenant integration."""
    try:
        print(f"[DEBUG] Testing connection for integration: {integration_id}")
        service = create_jira_service(tenant_id, integration_id, session)
        result = await service.test_connection()
        await service.close()
        return result
    except Exception as e:
        print(f"[DEBUG] Error in status endpoint: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/issues/{tenant_id}/{integration_id}")
async def list_jira_issues(
    tenant_id: UUID,
    integration_id: UUID,
    limit: Optional[int] = None,
    jql: Optional[str] = None,
    session: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """List all Jira issues for a specific tenant integration."""
    try:
        service = create_jira_service(tenant_id, integration_id, session)
        result = await service.list_issues(limit=limit, jql=jql)
        await service.close()
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/issues/{tenant_id}/{integration_id}/{issue_key}")
async def get_jira_issue(
    tenant_id: UUID,
    integration_id: UUID,
    issue_key: str,
    session: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get a specific Jira issue."""
    try:
        service = create_jira_service(tenant_id, integration_id, session)
        result = await service.get_issue(issue_key)
        await service.close()
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/issues/{tenant_id}/{integration_id}")
async def create_jira_issue(
    tenant_id: UUID,
    integration_id: UUID,
    project_key: str,
    summary: str,
    description: str,
    issue_type: str = "Task",
    session: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Create a new Jira issue."""
    try:
        service = create_jira_service(tenant_id, integration_id, session)
        result = await service.create_issue(project_key, summary, description, issue_type)
        await service.close()
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/issues/{tenant_id}/{integration_id}/{issue_key}")
async def update_jira_issue(
    tenant_id: UUID,
    integration_id: UUID,
    issue_key: str,
    updates: Dict[str, Any],
    session: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Update a Jira issue."""
    try:
        service = create_jira_service(tenant_id, integration_id, session)
        result = await service.update_issue(issue_key, updates)
        await service.close()
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/projects/{tenant_id}/{integration_id}")
async def list_jira_projects(
    tenant_id: UUID,
    integration_id: UUID,
    session: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """List all Jira projects for a specific tenant integration."""
    try:
        service = create_jira_service(tenant_id, integration_id, session)
        result = await service.list_projects()
        await service.close()
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sync/{tenant_id}/{integration_id}")
async def jira_sync(
    tenant_id: UUID,
    integration_id: UUID,
    background_tasks: BackgroundTasks,
    sync_type: str = "full",  # "full" or "incremental"
    session: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Trigger Jira sync for a specific tenant integration."""
    if sync_type not in ["full", "incremental"]:
        raise HTTPException(status_code=400, detail="sync_type must be 'full' or 'incremental'")
    
    try:
        # Test connection first
        service = create_jira_service(tenant_id, integration_id, session)
        connection_test = await service.test_connection()
        
        if not connection_test.get("connected"):
            await service.close()
            return {
                "success": False,
                "error": "Jira connection failed",
                "details": connection_test
            }
        
        # Run sync in background
        if sync_type == "full":
            background_tasks.add_task(_run_full_sync, tenant_id, integration_id)
        else:
            background_tasks.add_task(_run_incremental_sync, tenant_id, integration_id)
        
        await service.close()
        
        return {
            "success": True,
            "message": f"Jira {sync_type} sync started in background",
            "tenant_id": str(tenant_id),
            "integration_id": str(integration_id)
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


async def _run_full_sync(tenant_id: UUID, integration_id: UUID):
    """Background task for full sync."""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"Starting background full sync for tenant {tenant_id}, integration {integration_id}")
    
    try:
        async for session in get_db():
            service = create_jira_service(tenant_id, integration_id, session)
            
            # Fetch Jira issues
            logger.info("Fetching Jira issues...")
            issues_result = await service.list_issues()
            logger.info(f"Issues result: {issues_result}")
            
            if issues_result.get("success"):
                issues = issues_result.get("issues", [])
                logger.info(f"Fetched {len(issues)} Jira issues")
                
                # The AI clustering is already handled in the list_issues method
                # Just need to update the integration status
                
                # Update integration last_synced_at
                integration = await session.get(TenantIntegration, integration_id)
                if integration:
                    integration.last_synced_at = dt.datetime.utcnow()
                    integration.last_sync_status = "success"
                    integration.sync_error_message = None
                    await session.commit()
                
                result = {
                    "success": True,
                    "processed": len(issues),
                    "updated": len(issues),
                    "tenant_id": str(tenant_id)
                }
                logger.info(f"Background full sync completed: {result}")
                return result
            else:
                error_msg = f"Failed to fetch Jira issues: {issues_result.get('error')}"
                logger.error(error_msg)
                return {"success": False, "error": error_msg}
            
    except Exception as e:
        logger.error(f"Background full sync failed: {str(e)}")
        logger.exception("Full traceback:")
        return {"success": False, "error": str(e)}


async def _run_incremental_sync(tenant_id: UUID, integration_id: UUID):
    """Background task for incremental sync."""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"Starting background incremental sync for tenant {tenant_id}, integration {integration_id}")
    
    try:
        async for session in get_db():
            service = create_jira_service(tenant_id, integration_id, session)
            
            # For incremental sync, we could filter by updated date
            # For now, just do a full sync
            logger.info("Performing incremental sync (using full sync for now)...")
            issues_result = await service.list_issues()
            
            if issues_result.get("success"):
                issues = issues_result.get("issues", [])
                logger.info(f"Fetched {len(issues)} Jira issues")
                
                # Update integration last_synced_at
                integration = await session.get(TenantIntegration, integration_id)
                if integration:
                    integration.last_synced_at = dt.datetime.utcnow()
                    integration.last_sync_status = "success"
                    integration.sync_error_message = None
                    await session.commit()
                
                result = {
                    "success": True,
                    "processed": len(issues),
                    "updated": len(issues),
                    "tenant_id": str(tenant_id)
                }
                logger.info(f"Background incremental sync completed: {result}")
                return result
            else:
                error_msg = f"Failed to fetch Jira issues: {issues_result.get('error')}"
                logger.error(error_msg)
                return {"success": False, "error": error_msg}
            
    except Exception as e:
        logger.error(f"Background incremental sync failed: {str(e)}")
        logger.exception("Full traceback:")
        return {"success": False, "error": str(e)}


# -------------------------------------------------------------------------
# Tenant integration management
# -------------------------------------------------------------------------

@router.get("/integrations/{tenant_id}")
async def list_jira_integrations(
    tenant_id: UUID,
    session: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """List all Jira integrations for a tenant."""
    try:
        from sqlalchemy import select
        
        stmt = select(TenantIntegration).where(
            TenantIntegration.tenant_id == tenant_id,
            TenantIntegration.integration_type == "jira"
        )
        result = await session.execute(stmt)
        integrations = result.scalars().all()
        
        # Convert to dict format and include status
        integration_list = []
        for integration in integrations:
            integration_data = {
                "id": str(integration.id),
                "tenant_id": str(integration.tenant_id),
                "is_active": integration.is_active,
                "last_synced_at": integration.last_synced_at.isoformat() if integration.last_synced_at else None,
                "last_sync_status": integration.last_sync_status,
                "sync_error_message": integration.sync_error_message,
                "created_at": integration.created_at.isoformat(),
                "updated_at": integration.updated_at.isoformat()
            }
            
            # Test connection status
            try:
                service = create_jira_service(tenant_id, integration.id, session)
                status = await service.test_connection()
                integration_data["connection_status"] = status
                await service.close()
            except Exception as e:
                integration_data["connection_status"] = {"connected": False, "error": str(e)}
            
            integration_list.append(integration_data)
        
        return {
            "success": True,
            "integrations": integration_list,
            "total_count": len(integration_list),
            "tenant_id": str(tenant_id)
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


from pydantic import BaseModel

class JiraIntegrationCreate(BaseModel):
    access_token: str
    base_url: str
    email: str  # Add email field for Basic Auth

@router.post("/integrations/{tenant_id}")
async def create_jira_integration(
    tenant_id: UUID,
    integration_data: JiraIntegrationCreate,
    session: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Create a new Jira integration for a tenant with an access token and base URL."""
    try:
        import uuid
        
        # Validate the access token first
        service = create_jira_service(tenant_id, uuid.uuid4(), session)  # Temporary service for validation
        service._access_token = integration_data.access_token
        service._base_url = integration_data.base_url
        
        # Basic validation - just check format
        if not integration_data.access_token or len(integration_data.access_token) < 10:
            await service.close()
            raise HTTPException(
                status_code=400, 
                detail={
                    "error": "Invalid API token format",
                    "message": "Please provide a valid API token",
                    "suggestions": [
                        "Get your API token from https://id.atlassian.com/manage-profile/security/api-tokens",
                        "Ensure the token is at least 10 characters long",
                        "Check that you copied the entire token"
                    ]
                }
            )

        if not integration_data.base_url or not integration_data.base_url.startswith('https://'):
            await service.close()
            raise HTTPException(
                status_code=400, 
                detail={
                    "error": "Invalid base URL format",
                    "message": "Base URL must start with https://",
                    "suggestions": [
                        "Use format: https://your-domain.atlassian.net",
                        "Ensure the URL is accessible"
                    ]
                }
            )
        
        # Create the integration
        integration = TenantIntegration(
            tenant_id=tenant_id,
            integration_type="jira",
            is_active=True,
            config={
                "access_token": integration_data.access_token, 
                "base_url": integration_data.base_url,
                "email": integration_data.email
            }
        )
        
        session.add(integration)
        await session.commit()
        await session.refresh(integration)
        
        await service.close()
        
        return {
            "success": True,
            "integration_id": str(integration.id),
            "tenant_id": str(tenant_id),
            "message": "Jira integration created successfully"
        }
        
    except Exception as e:
        if "Invalid Jira access token" in str(e):
            raise e
        raise HTTPException(status_code=400, detail=str(e))


# -------------------------------------------------------------------------
# OAuth 2.0 authorization flow
# -------------------------------------------------------------------------

@router.get("/authorize/{tenant_id}")
async def jira_authorize_url(
    tenant_id: UUID,
    session: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Generate Jira OAuth authorization URL for a tenant."""
    try:
        import urllib.parse as up
        
        # Create a placeholder integration to get the ID for the OAuth state
        integration = TenantIntegration(
            tenant_id=tenant_id,
            integration_type="jira",
            is_active=False,  # Will be activated after OAuth completion
            config={}
        )
        
        session.add(integration)
        await session.commit()
        await session.refresh(integration)
        
        client_id = os.getenv("JIRA_CLIENT_ID")
        redirect_uri = os.getenv("JIRA_REDIRECT_URI")
        
        if not client_id or not redirect_uri:
            raise HTTPException(status_code=500, detail="Jira OAuth credentials not configured")
        
        scope = "read:jira-work"
        state = f"{str(tenant_id)[:8]}:{str(integration.id)[:8]}"
        
        qs = up.urlencode({
            "audience": "api.atlassian.com",
            "client_id": client_id,
            "scope": scope,
            "redirect_uri": redirect_uri,
            "state": state,
            "response_type": "code",
            "prompt": "consent"
        })
        
        url = f"https://auth.atlassian.com/authorize?{qs}"
        
        return {
            "success": True,
            "authorization_url": url,
            "integration_id": str(integration.id),
            "tenant_id": str(tenant_id)
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/oauth/callback")
async def jira_oauth_callback(
    code: str, 
    state: Optional[str] = None,
    session: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Handle OAuth callback and exchange code for access token."""
    try:
        import httpx
        
        # Debug: Log the received state
        print(f"[DEBUG] Received state: {state}")
        if state:
            print(f"[DEBUG] State length: {len(state)}")
        else:
            print("[DEBUG] No state parameter received")
        
        # If no state provided, we need to find the integration differently
        if not state:
            # Try to find the most recent Jira integration for any tenant
            from sqlalchemy import select
            stmt = select(TenantIntegration).where(
                TenantIntegration.integration_type == "jira"
            ).order_by(TenantIntegration.created_at.desc()).limit(1)
            
            result = await session.execute(stmt)
            integration = result.scalar_one_or_none()
            
            if not integration:
                raise HTTPException(
                    status_code=400, 
                    detail="No Jira integration found. Please create an integration first."
                )
            
            tenant_id = integration.tenant_id
            integration_id = integration.id
            print(f"[DEBUG] Using most recent integration: tenant_id={tenant_id}, integration_id={integration_id}")
        else:
            # Check if state contains the expected format
            if ":" not in state:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Invalid state format. Expected 'tenant_id:integration_id', got: {state}"
                )
            
            # Parse state
            tenant_id_str, integration_id_str = state.split(":", 1)
            print(f"[DEBUG] Parsed tenant_id: {tenant_id_str}")
            print(f"[DEBUG] Parsed integration_id: {integration_id_str}")
            
            # Handle both full UUID and shortened formats
            try:
                # Try to parse as full UUID first
                tenant_id = UUID(tenant_id_str)
                integration_id = UUID(integration_id_str)
            except ValueError:
                # If that fails, try to find the integration by the shortened ID
                from sqlalchemy import select, cast, String
                stmt = select(TenantIntegration).where(
                    cast(TenantIntegration.id, String).like(f"{integration_id_str}%")
                )
                result = await session.execute(stmt)
                integration = result.scalar_one_or_none()
                
                if not integration:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Could not find integration with ID starting with: {integration_id_str}"
                    )
                
                tenant_id = integration.tenant_id
                integration_id = integration.id
        
        # Exchange code for token
        client_id = os.getenv("JIRA_CLIENT_ID")
        client_secret = os.getenv("JIRA_CLIENT_SECRET")
        redirect_uri = os.getenv("JIRA_REDIRECT_URI")
        
        if not all([client_id, client_secret, redirect_uri]):
            raise HTTPException(status_code=500, detail="Jira OAuth credentials not configured")
        
        token_data = {
            "grant_type": "authorization_code",
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "code": code,
        }
        
        # Exchange code for token
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://auth.atlassian.com/oauth/token",
                data=token_data,
                timeout=15
            )
            response.raise_for_status()
            token_response = response.json()
        
        access_token = token_response.get("access_token")
        refresh_token = token_response.get("refresh_token")
        
        print(f"[DEBUG] Token response keys: {list(token_response.keys())}")
        print(f"[DEBUG] Access token: {access_token[:20]}..." if access_token else "None")
        print(f"[DEBUG] Token type: {token_response.get('token_type', 'unknown')}")
        print(f"[DEBUG] Scope: {token_response.get('scope', 'unknown')}")
        
        if not access_token:
            raise HTTPException(status_code=400, detail="Failed to obtain access token")
        
        # Get accessible Jira instances (this is the correct endpoint)
        async with httpx.AsyncClient() as client:
            instances_response = await client.get(
                "https://api.atlassian.com/oauth/token/accessible-resources",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            instances_response.raise_for_status()
            instances = instances_response.json()
        
        if not instances:
            raise HTTPException(status_code=400, detail="No accessible Jira instances found")
        
        # Use the first accessible instance (user can change this later)
        base_url = instances[0]["url"]
        
        # Skip user info call since we don't have the right scope
        print(f"[DEBUG] Skipping user info call - using accessible resources data")
        user_info = {
            "account_id": instances[0].get("id", "unknown"),
            "name": instances[0].get("name", "Jira Instance"),
            "url": instances[0].get("url", base_url)
        }
        
        # Use the first accessible instance (user can change this later)
        base_url = instances[0]["url"]
        
        # Skip token validation since OAuth token is for Atlassian Cloud, not Jira instance
        print(f"[DEBUG] Skipping token validation - OAuth token is valid for Atlassian Cloud APIs")
        
        # Update integration with token and activate it
        integration.config = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "base_url": base_url,
            "user_info": user_info,
            "instances": instances
        }
        integration.is_active = True
        await session.commit()
        
        # Redirect to frontend integrations page
        from fastapi.responses import RedirectResponse
        
        frontend_url = f"http://localhost:3000/integrations?success=true&integration_id={integration_id}&provider=jira"  # Adjust this to your frontend URL
        return RedirectResponse(url=frontend_url, status_code=302)
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# -------------------------------------------------------------------------
# Legacy endpoints (for backward compatibility)
# -------------------------------------------------------------------------

@router.post("/match-all")
async def jira_match_all() -> Dict[str, int | bool]:
    """Attempt to match all issues without Jira keys (stubbed)."""
    return {"success": True, "matched": 0}
