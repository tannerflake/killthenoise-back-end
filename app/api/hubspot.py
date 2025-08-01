from __future__ import annotations

import os
from typing import Dict, List, Any, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.tenant_integration import TenantIntegration
from app.services.hubspot_service import create_hubspot_service

router = APIRouter(prefix="/api/hubspot", tags=["HubSpot"])


# -------------------------------------------------------------------------
# Multi-tenant HubSpot endpoints
# -------------------------------------------------------------------------

@router.get("/status/{tenant_id}/{integration_id}")
async def hubspot_status(
    tenant_id: UUID, 
    integration_id: UUID,
    session: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Test HubSpot connection status for a specific tenant integration."""
    try:
        service = create_hubspot_service(tenant_id, integration_id)
        result = await service.test_connection()
        await service.close()
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/tickets/{tenant_id}/{integration_id}")
async def list_hubspot_tickets(
    tenant_id: UUID,
    integration_id: UUID,
    limit: Optional[int] = None,
    session: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """List all HubSpot tickets for a specific tenant integration."""
    try:
        service = create_hubspot_service(tenant_id, integration_id)
        result = await service.list_tickets(limit=limit)
        await service.close()
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sync/{tenant_id}/{integration_id}")
async def hubspot_sync(
    tenant_id: UUID,
    integration_id: UUID,
    background_tasks: BackgroundTasks,
    sync_type: str = "full",  # "full" or "incremental"
    session: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Trigger HubSpot sync for a specific tenant integration."""
    if sync_type not in ["full", "incremental"]:
        raise HTTPException(status_code=400, detail="sync_type must be 'full' or 'incremental'")
    
    try:
        # Test connection first
        service = create_hubspot_service(tenant_id, integration_id)
        connection_test = await service.test_connection()
        
        if not connection_test.get("connected"):
            await service.close()
            return {
                "success": False,
                "error": "HubSpot connection failed",
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
            "message": f"HubSpot {sync_type} sync started in background",
            "tenant_id": str(tenant_id),
            "integration_id": str(integration_id)
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


async def _run_full_sync(tenant_id: UUID, integration_id: UUID):
    """Background task for full sync."""
    service = create_hubspot_service(tenant_id, integration_id)
    try:
        await service.sync_full()
    finally:
        await service.close()


async def _run_incremental_sync(tenant_id: UUID, integration_id: UUID):
    """Background task for incremental sync."""
    service = create_hubspot_service(tenant_id, integration_id)
    try:
        await service.sync_incremental()
    finally:
        await service.close()


# -------------------------------------------------------------------------
# Tenant integration management
# -------------------------------------------------------------------------

@router.get("/integrations/{tenant_id}")
async def list_hubspot_integrations(
    tenant_id: UUID,
    session: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """List all HubSpot integrations for a tenant."""
    try:
        from sqlalchemy import select
        
        stmt = select(TenantIntegration).where(
            TenantIntegration.tenant_id == tenant_id,
            TenantIntegration.integration_type == "hubspot"
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
                service = create_hubspot_service(tenant_id, integration.id)
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


@router.post("/integrations/{tenant_id}")
async def create_hubspot_integration(
    tenant_id: UUID,
    access_token: str,
    session: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Create a new HubSpot integration for a tenant with an access token."""
    try:
        import uuid
        
        # Validate the access token first
        service = create_hubspot_service(tenant_id, uuid.uuid4())  # Temporary service for validation
        service._access_token = access_token
        
        # Test the token
        is_valid = await service._validate_token(access_token)
        if not is_valid:
            await service.close()
            raise HTTPException(status_code=400, detail="Invalid HubSpot access token")
        
        # Create the integration
        integration = TenantIntegration(
            tenant_id=tenant_id,
            integration_type="hubspot",
            is_active=True,
            config={"access_token": access_token}
        )
        
        session.add(integration)
        await session.commit()
        await session.refresh(integration)
        
        await service.close()
        
        return {
            "success": True,
            "integration_id": str(integration.id),
            "tenant_id": str(tenant_id),
            "message": "HubSpot integration created successfully"
        }
        
    except Exception as e:
        if "Invalid HubSpot access token" in str(e):
            raise e
        raise HTTPException(status_code=400, detail=str(e))


# -------------------------------------------------------------------------
# OAuth 2.0 authorization flow
# -------------------------------------------------------------------------

@router.get("/authorize/{tenant_id}")
async def hubspot_authorize_url(
    tenant_id: UUID,
    session: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Generate HubSpot OAuth authorization URL for a tenant."""
    try:
        import urllib.parse as up
        
        # Create a placeholder integration to get the ID for the OAuth state
        integration = TenantIntegration(
            tenant_id=tenant_id,
            integration_type="hubspot",
            is_active=False,  # Will be activated after OAuth completion
            config={}
        )
        
        session.add(integration)
        await session.commit()
        await session.refresh(integration)
        
        client_id = os.getenv("HUBSPOT_CLIENT_ID")
        redirect_uri = os.getenv("HUBSPOT_REDIRECT_URI")
        
        if not client_id or not redirect_uri:
            raise HTTPException(status_code=500, detail="HubSpot OAuth credentials not configured")
        
        scope = "oauth%20tickets"
        state = f"{tenant_id}:{integration.id}"
        
        qs = up.urlencode({
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "state": state,
        })
        
        url = f"https://app.hubspot.com/oauth/authorize?{qs}"
        
        return {
            "success": True,
            "authorization_url": url,
            "integration_id": str(integration.id),
            "tenant_id": str(tenant_id)
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/oauth/callback")
async def hubspot_oauth_callback(
    code: str, 
    state: str,
    session: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Handle OAuth callback and exchange code for access token."""
    try:
        import httpx
        
        # Parse state
        tenant_id_str, integration_id_str = state.split(":", 1)
        tenant_id = UUID(tenant_id_str)
        integration_id = UUID(integration_id_str)
        
        # Get the integration
        integration = await session.get(TenantIntegration, integration_id)
        if not integration or integration.tenant_id != tenant_id:
            raise HTTPException(status_code=400, detail="Invalid OAuth state")
        
        # Exchange code for token
        client_id = os.getenv("HUBSPOT_CLIENT_ID")
        client_secret = os.getenv("HUBSPOT_CLIENT_SECRET")
        redirect_uri = os.getenv("HUBSPOT_REDIRECT_URI")
        
        if not all([client_id, client_secret, redirect_uri]):
            raise HTTPException(status_code=500, detail="HubSpot OAuth credentials not configured")
        
        token_data = {
            "grant_type": "authorization_code",
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "code": code,
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.hubapi.com/oauth/v1/token",
                data=token_data,
                timeout=15
            )
            response.raise_for_status()
            token_response = response.json()
        
        access_token = token_response.get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="Failed to obtain access token")
        
        # Validate the token
        service = create_hubspot_service(tenant_id, integration_id)
        is_valid = await service._validate_token(access_token)
        
        if not is_valid:
            await service.close()
            raise HTTPException(status_code=400, detail="Received invalid access token from HubSpot")
        
        # Update integration with token and activate it
        integration.config = {"access_token": access_token}
        integration.is_active = True
        await session.commit()
        
        await service.close()
        
        return {
            "success": True,
            "integration_id": str(integration_id),
            "tenant_id": str(tenant_id),
            "message": "HubSpot integration activated successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# -------------------------------------------------------------------------
# Legacy endpoints (for backward compatibility)
# -------------------------------------------------------------------------

@router.get("/status", response_model=Dict[str, bool])
async def hubspot_status_legacy() -> Dict[str, bool]:
    """Legacy status endpoint - returns generic status."""
    return {"connected": True, "note": "Use /status/{tenant_id}/{integration_id} for actual testing"}
