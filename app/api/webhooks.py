from __future__ import annotations

import hashlib
import hmac
from typing import Any, Dict
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select

from app.db import get_db
from app.models.tenant_integration import TenantIntegration
from app.services.hubspot_service import create_hubspot_service

router = APIRouter(prefix="/api/webhooks", tags=["Webhooks"])


class WebhookPayload(BaseModel):
    """Base webhook payload model."""

    pass


@router.post("/hubspot/{tenant_id}")
async def hubspot_webhook(
    tenant_id: UUID,
    request: Request,
    x_hubspot_signature: str | None = Header(None),
    x_hubspot_signature_version: str | None = Header(None),
) -> Dict[str, Any]:
    """Handle HubSpot webhook for real-time updates."""

    # Get the raw body for signature verification
    body = await request.body()

    # Verify webhook signature (implement proper verification)
    if x_hubspot_signature:
        # TODO: Implement proper signature verification
        # For now, we'll skip verification in development
        pass

    # Parse the webhook payload
    try:
        webhook_data = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON payload: {e}")

    # Find the HubSpot integration for this tenant
    async for session in get_db():
        stmt = select(TenantIntegration).where(
            TenantIntegration.tenant_id == tenant_id,
            TenantIntegration.integration_type == "hubspot",
            TenantIntegration.is_active == True,
        )
        result = await session.execute(stmt)
        integration = result.scalar_one_or_none()

        if not integration:
            raise HTTPException(
                status_code=404,
                detail=f"No active HubSpot integration found for tenant {tenant_id}",
            )

        # Process the webhook
        try:
            service = create_hubspot_service(tenant_id, integration.id)
            result = await service.process_webhook(webhook_data)
            return result
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error processing webhook: {str(e)}"
            )


@router.post("/jira/{tenant_id}")
async def jira_webhook(tenant_id: UUID, request: Request) -> Dict[str, Any]:
    """Handle Jira webhook for real-time updates."""
    # TODO: Implement Jira webhook handling
    webhook_data = await request.json()

    return {
        "success": True,
        "message": "Jira webhook received (not yet implemented)",
        "tenant_id": str(tenant_id),
    }


@router.get("/health")
async def webhook_health() -> Dict[str, Any]:
    """Health check for webhook endpoints."""
    return {
        "status": "healthy",
        "endpoints": {
            "hubspot": "/api/webhooks/hubspot/{tenant_id}",
            "jira": "/api/webhooks/jira/{tenant_id}",
        },
    }
