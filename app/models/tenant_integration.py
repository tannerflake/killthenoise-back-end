from __future__ import annotations

import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, String, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.db import Base


class TenantIntegration(Base):
    __tablename__ = "tenant_integrations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    integration_type = Column(String, nullable=False)  # 'hubspot', 'jira', etc.
    is_active = Column(Boolean, default=True)
    
    # Integration-specific config (encrypted in production)
    config = Column(JSON, nullable=False)  # API keys, domains, etc.
    
    # Sync tracking
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    last_sync_status = Column(String, nullable=True)  # 'success', 'failed', 'partial'
    sync_error_message = Column(String, nullable=True)
    
    # Webhook configuration
    webhook_url = Column(String, nullable=True)
    webhook_secret = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    class Config:
        orm_mode = True 