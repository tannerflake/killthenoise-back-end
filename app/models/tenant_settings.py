from __future__ import annotations

from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.db import Base


class TenantSettings(Base):
    __tablename__ = "tenant_settings"

    tenant_id = Column(UUID(as_uuid=True), primary_key=True)
    grouping_instructions = Column(Text, nullable=True)
    type_classification_instructions = Column(Text, nullable=True)
    severity_calculation_instructions = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
