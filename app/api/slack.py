from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.tenant_integration import TenantIntegration
from app.services.slack_service import SlackService


router = APIRouter(prefix="/api/slack", tags=["Slack"])


class SlackIntegrationCreate(BaseModel):
    token: str
    team: Optional[str] = None


class SlackChannelsUpdate(BaseModel):
    channel_ids: List[str]


def create_slack_service(tenant_id: UUID, integration_id: Optional[UUID] = None) -> SlackService:
    """Create a SlackService instance with proper session management."""
    from app.db import AsyncSessionLocal
    session = AsyncSessionLocal()
    return SlackService(tenant_id, integration_id, session)


@router.get("/auth-status/{tenant_id}")
async def slack_auth_status(
    tenant_id: UUID,
    session: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Check if a tenant has an active Slack integration with valid tokens."""
    try:
        # Find active Slack integration for this tenant
        from sqlalchemy import and_, select
        stmt = select(TenantIntegration).where(
            and_(
                TenantIntegration.tenant_id == tenant_id,
                TenantIntegration.integration_type == "slack",
                TenantIntegration.is_active == True
            )
        )
        result = await session.execute(stmt)
        integrations = result.scalars().all()
        
        if not integrations:
            return {
                "authenticated": False,
                "message": "No active Slack integration found",
                "needs_auth": True,
                "can_refresh": False
            }
        
        if len(integrations) > 1:
            return {
                "authenticated": False,
                "message": "Multiple Slack integrations found - please clean up duplicates",
                "needs_auth": True,
                "can_refresh": False
            }
        
        integration = integrations[0]
        config = integration.config or {}
        
        # Check if we have OAuth tokens
        access_token = config.get("access_token")
        refresh_token = config.get("refresh_token")
        
        if not access_token:
            return {
                "authenticated": False,
                "message": "Slack integration found but no access token available",
                "needs_auth": True,
                "can_refresh": False,
                "integration_id": str(integration.id)
            }
        
        # Try to validate the token by making a test API call
        service = create_slack_service(tenant_id, integration.id)
        try:
            # This will attempt to refresh the token if needed
            await service._get_valid_token(session)
            
            # Get team info if available
            team_info = config.get("team")
            
            return {
                "authenticated": True,
                "message": "Slack integration is active and working",
                "needs_auth": False,
                "can_refresh": bool(refresh_token),
                "integration_id": str(integration.id),
                "team": team_info,
                "scopes": ["channels:read", "channels:history", "groups:read", "groups:history"]
            }
            
        except ValueError as e:
            # Token is invalid or expired
            if refresh_token:
                return {
                    "authenticated": False,
                    "message": f"Token validation failed: {str(e)}",
                    "needs_auth": False,
                    "can_refresh": True,
                    "integration_id": str(integration.id)
                }
            else:
                return {
                    "authenticated": False,
                    "message": f"Token validation failed: {str(e)}",
                    "needs_auth": True,
                    "can_refresh": False,
                    "integration_id": str(integration.id)
                }
        finally:
            await service.close()
            
    except Exception as e:
        return {
            "authenticated": False,
            "message": f"Error checking authentication status: {str(e)}",
            "needs_auth": True,
            "can_refresh": False
        }


@router.get("/authorize/{tenant_id}")
async def slack_authorize_url(
    tenant_id: UUID,
    session: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Generate OAuth authorization URL for Slack."""
    try:
        client_id = os.getenv("SLACK_CLIENT_ID")
        redirect_uri = os.getenv("SLACK_REDIRECT_URI")
        
        if not client_id or not redirect_uri:
            raise HTTPException(status_code=500, detail="Slack OAuth credentials not configured")
        
        # Create a temporary integration record to store the state
        from app.models.tenant_integration import TenantIntegration
        integration = TenantIntegration(
            tenant_id=tenant_id,
            integration_type="slack",
            is_active=False,  # Will be activated after OAuth completion
            config={"oauth_state": "pending"}
        )
        session.add(integration)
        await session.commit()
        await session.refresh(integration)
        
        # Build authorization URL
        scopes = "channels:read,channels:history,groups:read,groups:history"
        state = f"{tenant_id}:{integration.id}"
        
        auth_url = (
            f"https://slack.com/oauth/v2/authorize"
            f"?client_id={client_id}"
            f"&scope={scopes}"
            f"&redirect_uri={redirect_uri}"
            f"&state={state}"
        )
        
        return {
            "success": True,
            "authorization_url": auth_url,
            "integration_id": str(integration.id),
            "tenant_id": str(tenant_id)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/oauth/callback")
async def slack_oauth_callback(
    code: str, 
    state: str,
    session: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Handle OAuth callback and exchange code for access token."""
    try:
        # Parse state
        tenant_id_str, integration_id_str = state.split(":", 1)
        tenant_id = UUID(tenant_id_str)
        integration_id = UUID(integration_id_str)
        
        # Get the integration
        integration = await session.get(TenantIntegration, integration_id)
        if not integration or integration.tenant_id != tenant_id:
            raise HTTPException(status_code=400, detail="Invalid OAuth state")
        
        # Exchange code for token
        client_id = os.getenv("SLACK_CLIENT_ID")
        client_secret = os.getenv("SLACK_CLIENT_SECRET")
        redirect_uri = os.getenv("SLACK_REDIRECT_URI")
        
        if not all([client_id, client_secret, redirect_uri]):
            raise HTTPException(status_code=500, detail="Slack OAuth credentials not configured")
        
        token_data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://slack.com/api/oauth.v2.access",
                data=token_data,
                timeout=15
            )
            response.raise_for_status()
            token_response = response.json()
        
        if not token_response.get("ok"):
            raise HTTPException(status_code=400, detail=f"Slack OAuth error: {token_response.get('error')}")
        
        access_token = token_response.get("access_token")
        refresh_token = token_response.get("refresh_token")
        expires_in = token_response.get("expires_in", 3600)
        team = token_response.get("team", {}).get("name")
        
        if not access_token:
            raise HTTPException(status_code=400, detail="Failed to obtain access token")
        
        # Update the integration with OAuth tokens
        integration.config = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": expires_in,
            "token_created_at": "2024-01-01T00:00:00",  # Will be updated by service
            "team": team,
            "channels": []
        }
        integration.is_active = True
        
        await session.commit()
        
        # Create success HTML response
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Slack Connected Successfully</title>
            <style>
                body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                .success { color: #36a64f; font-size: 24px; margin-bottom: 20px; }
                .message { color: #666; margin-bottom: 30px; }
                .close { background: #36a64f; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }
            </style>
        </head>
        <body>
            <div class="success">✅ Slack Connected Successfully!</div>
            <div class="message">Your Slack workspace has been connected to KillTheNoise.</div>
            <button class="close" onclick="window.close()">Close Window</button>
        </body>
        </html>
        """
        
        from fastapi.responses import Response
        return Response(content=html_content, media_type="text/html")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/refresh-token/{tenant_id}/{integration_id}")
async def slack_refresh_token(
    tenant_id: UUID,
    integration_id: UUID,
    session: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Manually refresh the access token for a Slack integration."""
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
        service = create_slack_service(tenant_id, integration_id)
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

def _service(tenant_id: str, session: AsyncSession) -> SlackService:
    return SlackService(UUID(tenant_id), session=session)


@router.post("/integrations/{tenant_id}")
async def create_slack_integration(
    tenant_id: str,
    payload: SlackIntegrationCreate,
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Create a Slack integration with bot token (legacy method)."""
    service = _service(tenant_id, session)
    result = await service.create_integration(token=payload.token, team=payload.team)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result)
    return result


@router.get("/channels/{tenant_id}")
async def list_slack_channels(
    tenant_id: str,
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """List available Slack channels."""
    service = _service(tenant_id, session)
    return await service.list_channels()


@router.post("/channels/{tenant_id}")
async def update_slack_channels(
    tenant_id: str,
    payload: SlackChannelsUpdate,
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Update selected Slack channels."""
    service = _service(tenant_id, session)
    return await service.update_selected_channels(channel_ids=payload.channel_ids)


@router.post("/sync/{tenant_id}")
async def sync_slack_messages(
    tenant_id: str,
    lookback_days: int = Query(7, ge=1, le=60),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Sync Slack messages."""
    service = _service(tenant_id, session)
    return await service.sync_messages(lookback_days=lookback_days)

