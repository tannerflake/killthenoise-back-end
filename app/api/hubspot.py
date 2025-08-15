from __future__ import annotations

import datetime as dt
import os
from typing import Dict, List, Any, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends, Response
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
        result = await service.test_connection(session)
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
        result = await service.list_tickets(session, limit=limit)
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
        connection_test = await service.test_connection(session)
        
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
                status = await service.test_connection(session)
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

@router.get("/auth-status/{tenant_id}")
async def hubspot_auth_status(
    tenant_id: UUID,
    session: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Check if a tenant has an active HubSpot integration that can be used."""
    try:
        from sqlalchemy import select
        
        # Find the most recent active HubSpot integration for this tenant
        stmt = select(TenantIntegration).where(
            TenantIntegration.tenant_id == tenant_id,
            TenantIntegration.integration_type == "hubspot",
            TenantIntegration.is_active == True
        ).order_by(TenantIntegration.created_at.desc())
        
        result = await session.execute(stmt)
        integrations = result.scalars().all()
        
        # Use the most recent integration
        integration = integrations[0] if integrations else None
        
        if not integration:
            return {
                "authenticated": False,
                "message": "No active HubSpot integration found",
                "needs_auth": True
            }
        
        # Check if we have a valid token
        has_token = bool(integration.config.get("access_token"))
        has_refresh_token = bool(integration.config.get("refresh_token"))
        
        if not has_token:
            return {
                "authenticated": False,
                "message": "Integration exists but no access token configured",
                "needs_auth": True,
                "integration_id": str(integration.id)
            }
        
        # Test the connection
        try:
            service = create_hubspot_service(tenant_id, integration.id)
            status = await service.test_connection(session)
            await service.close()
            
            if status.get("connected"):
                return {
                    "authenticated": True,
                    "message": "HubSpot integration is active and working",
                    "needs_auth": False,
                    "integration_id": str(integration.id),
                    "hub_domain": status.get("hub_domain"),
                    "scopes": status.get("scopes", [])
                }
            else:
                # If we have a refresh token, we can try to refresh
                if has_refresh_token:
                    return {
                        "authenticated": False,
                        "message": "Token expired but refresh token available",
                        "needs_auth": False,
                        "can_refresh": True,
                        "integration_id": str(integration.id)
                    }
                else:
                    return {
                        "authenticated": False,
                        "message": "Token expired and no refresh token available",
                        "needs_auth": True,
                        "integration_id": str(integration.id)
                    }
                    
        except Exception as e:
            return {
                "authenticated": False,
                "message": f"Error testing connection: {str(e)}",
                "needs_auth": True,
                "integration_id": str(integration.id)
            }
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


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
        
        # Use correct HubSpot scopes for ticket access
        scope = "tickets"
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


@router.get("/oauth/callback")
async def hubspot_oauth_callback(
    code: str, 
    state: str,
    session: AsyncSession = Depends(get_db)
) -> Response:
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
        refresh_token = token_response.get("refresh_token")
        expires_in = token_response.get("expires_in", 3600)  # Default to 1 hour
        
        if not access_token:
            raise HTTPException(status_code=400, detail="Failed to obtain access token")
        
        # Validate the token
        service = create_hubspot_service(tenant_id, integration_id)
        is_valid = await service._validate_token(access_token)
        
        if not is_valid:
            await service.close()
            raise HTTPException(status_code=400, detail="Received invalid access token from HubSpot")
        
        # Update integration with tokens and activate it
        integration.config = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": expires_in,
            "token_created_at": dt.datetime.utcnow().isoformat()
        }
        integration.is_active = True
        await session.commit()
        
        await service.close()
        
        # Return HTML redirect to success page
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>HubSpot Integration Success</title>
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                .success {{ color: #28a745; font-size: 24px; margin-bottom: 20px; }}
                .details {{ color: #666; margin-bottom: 30px; }}
                .close {{ background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }}
            </style>
        </head>
        <body>
            <div class="success">✅ HubSpot Integration Successful!</div>
            <div class="details">
                <p>Your HubSpot integration has been activated successfully.</p>
                <p><strong>Integration ID:</strong> {integration_id}</p>
                <p><strong>Tenant ID:</strong> {tenant_id}</p>
            </div>
            <button class="close" onclick="window.close()">Close Window</button>
        </body>
        </html>
        """
        
        return Response(content=html_content, media_type="text/html")
        
    except Exception as e:
        # Return error page
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>HubSpot Integration Error</title>
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                .error {{ color: #dc3545; font-size: 24px; margin-bottom: 20px; }}
                .details {{ color: #666; margin-bottom: 30px; }}
                .close {{ background: #6c757d; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }}
            </style>
        </head>
        <body>
            <div class="error">❌ HubSpot Integration Failed</div>
            <div class="details">
                <p>There was an error activating your HubSpot integration.</p>
                <p><strong>Error:</strong> {str(e)}</p>
            </div>
            <button class="close" onclick="window.close()">Close Window</button>
        </body>
        </html>
        """
        
        return Response(content=html_content, media_type="text/html")


@router.post("/refresh-token/{tenant_id}/{integration_id}")
async def hubspot_refresh_token(
    tenant_id: UUID,
    integration_id: UUID,
    session: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Manually refresh the access token for a HubSpot integration."""
    try:
        # Get the integration
        integration = await session.get(TenantIntegration, integration_id)
        if not integration or integration.tenant_id != tenant_id:
            raise HTTPException(status_code=400, detail="Integration not found")
        
        if not integration.is_active:
            raise HTTPException(status_code=400, detail="Integration is not active")
        
        refresh_token = integration.config.get("refresh_token")
        if not refresh_token:
            raise HTTPException(status_code=400, detail="No refresh token available")
        
        # Use the service to refresh the token
        service = create_hubspot_service(tenant_id, integration_id)
        new_token = await service._refresh_access_token(session, integration, refresh_token)
        await service.close()
        
        if new_token:
            return {
                "success": True,
                "message": "Token refreshed successfully",
                "integration_id": str(integration_id),
                "tenant_id": str(tenant_id)
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to refresh token")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# -------------------------------------------------------------------------
# Legacy endpoints (for backward compatibility)
# -------------------------------------------------------------------------

@router.get("/status", response_model=Dict[str, bool])
async def hubspot_status_legacy() -> Dict[str, bool]:
    """Legacy status endpoint - returns generic status."""
    return {"connected": True, "note": "Use /status/{tenant_id}/{integration_id} for actual testing"}
