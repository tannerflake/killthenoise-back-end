from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, UUID4


class TenantSettingsBase(BaseModel):
    grouping_instructions: Optional[str] = None
    type_classification_instructions: Optional[str] = None
    severity_calculation_instructions: Optional[str] = None


class TenantSettingsCreate(TenantSettingsBase):
    tenant_id: UUID4


class TenantSettingsUpdate(TenantSettingsBase):
    pass


class TenantSettings(TenantSettingsBase):
    tenant_id: UUID4
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
