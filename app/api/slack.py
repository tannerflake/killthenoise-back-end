from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.services.slack_service import SlackService


router = APIRouter(prefix="/api/slack", tags=["Slack"])


class SlackIntegrationCreate(BaseModel):
    token: str
    team: Optional[str] = None


class SlackChannelsUpdate(BaseModel):
    channel_ids: List[str]


def _service(tenant_id: str, session: AsyncSession) -> SlackService:
    return SlackService(UUID(tenant_id), session)


@router.post("/integrations/{tenant_id}")
async def create_slack_integration(
    tenant_id: str,
    payload: SlackIntegrationCreate,
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
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
    service = _service(tenant_id, session)
    return await service.list_channels()


@router.post("/channels/{tenant_id}")
async def update_slack_channels(
    tenant_id: str,
    payload: SlackChannelsUpdate,
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = _service(tenant_id, session)
    return await service.update_selected_channels(channel_ids=payload.channel_ids)


@router.post("/sync/{tenant_id}")
async def sync_slack_messages(
    tenant_id: str,
    lookback_days: int = Query(7, ge=1, le=60),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = _service(tenant_id, session)
    return await service.sync_messages(lookback_days=lookback_days)

