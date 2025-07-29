from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.db import Base


class SyncEvent(Base):
    __tablename__ = "sync_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    integration_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Event details
    event_type = Column(String, nullable=False)  # 'webhook', 'polling', 'full_sync'
    status = Column(String, nullable=False)  # 'success', 'failed', 'partial'

    # Change tracking
    items_processed = Column(Integer, default=0)
    items_created = Column(Integer, default=0)
    items_updated = Column(Integer, default=0)
    items_deleted = Column(Integer, default=0)

    # Timing
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)

    # Error tracking
    error_message = Column(Text, nullable=True)
    error_details = Column(JSON, nullable=True)

    # Source data for debugging
    source_data = Column(JSON, nullable=True)  # Raw data from integration

    created_at = Column(DateTime(timezone=True), server_default=func.now())
