from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant_settings import TenantSettings
from app.schemas.tenant_settings import TenantSettingsCreate, TenantSettingsUpdate


class TenantSettingsService:
    """Service for managing tenant-specific settings and instructions."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_settings(self, tenant_id: UUID) -> Optional[TenantSettings]:
        """Get settings for a specific tenant."""
        stmt = select(TenantSettings).where(TenantSettings.tenant_id == tenant_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def create_or_update_settings(
        self, tenant_id: UUID, settings_data: TenantSettingsUpdate
    ) -> TenantSettings:
        """Create or update settings for a tenant."""
        # Try to get existing settings
        existing_settings = await self.get_settings(tenant_id)
        
        if existing_settings:
            # Update existing settings
            for field, value in settings_data.dict(exclude_unset=True).items():
                setattr(existing_settings, field, value)
            await self.session.commit()
            await self.session.refresh(existing_settings)
            return existing_settings
        else:
            # Create new settings
            new_settings = TenantSettings(
                tenant_id=tenant_id,
                **settings_data.dict(exclude_unset=True)
            )
            self.session.add(new_settings)
            await self.session.commit()
            await self.session.refresh(new_settings)
            return new_settings

    async def get_grouping_instructions(self, tenant_id: UUID) -> Optional[str]:
        """Get grouping instructions for a tenant."""
        settings = await self.get_settings(tenant_id)
        return settings.grouping_instructions if settings else None

    async def get_type_classification_instructions(self, tenant_id: UUID) -> Optional[str]:
        """Get type classification instructions for a tenant."""
        settings = await self.get_settings(tenant_id)
        return settings.type_classification_instructions if settings else None

    async def get_severity_calculation_instructions(self, tenant_id: UUID) -> Optional[str]:
        """Get severity calculation instructions for a tenant."""
        settings = await self.get_settings(tenant_id)
        return settings.severity_calculation_instructions if settings else None
