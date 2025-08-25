from __future__ import annotations

from typing import Any, Dict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.schemas.tenant_settings import TenantSettings, TenantSettingsUpdate
from app.services.tenant_settings_service import TenantSettingsService

router = APIRouter(prefix="/api/settings", tags=["Settings"])


@router.get("/general/{tenant_id}")
async def get_general_settings(
    tenant_id: str,
    session: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get general settings for a tenant."""
    try:
        tenant_uuid = UUID(tenant_id)
        settings_service = TenantSettingsService(session)
        settings = await settings_service.get_settings(tenant_uuid)
        
        if not settings:
            # Return default empty settings
            return {
                "success": True,
                "data": {
                    "tenant_id": tenant_id,
                    "grouping_instructions": "",
                    "type_classification_instructions": "",
                    "severity_calculation_instructions": "",
                    "created_at": None,
                    "updated_at": None
                }
            }
        
        return {
            "success": True,
            "data": {
                "tenant_id": str(settings.tenant_id),
                "grouping_instructions": settings.grouping_instructions or "",
                "type_classification_instructions": settings.type_classification_instructions or "",
                "severity_calculation_instructions": settings.severity_calculation_instructions or "",
                "created_at": settings.created_at.isoformat() if settings.created_at else None,
                "updated_at": settings.updated_at.isoformat() if settings.updated_at else None
            }
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid tenant ID format")
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.put("/general/{tenant_id}")
async def update_general_settings(
    tenant_id: str,
    settings_data: TenantSettingsUpdate,
    session: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Update general settings for a tenant."""
    try:
        tenant_uuid = UUID(tenant_id)
        settings_service = TenantSettingsService(session)
        updated_settings = await settings_service.create_or_update_settings(tenant_uuid, settings_data)
        
        return {
            "success": True,
            "data": {
                "tenant_id": str(updated_settings.tenant_id),
                "grouping_instructions": updated_settings.grouping_instructions or "",
                "type_classification_instructions": updated_settings.type_classification_instructions or "",
                "severity_calculation_instructions": updated_settings.severity_calculation_instructions or "",
                "created_at": updated_settings.created_at.isoformat() if updated_settings.created_at else None,
                "updated_at": updated_settings.updated_at.isoformat() if updated_settings.updated_at else None
            },
            "message": "Settings updated successfully"
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid tenant ID format")
    except Exception as e:
        return {"success": False, "error": str(e)}
