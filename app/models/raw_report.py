from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import Column, DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.db import Base


class RawReport(Base):
    __tablename__ = "raw_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Source info
    source = Column(String, nullable=False)  # e.g., hubspot, jira, slack
    external_id = Column(String, nullable=True, index=True)
    url = Column(String, nullable=True)

    # Content
    title = Column(String, nullable=False)
    body = Column(Text, nullable=True)

    # Optional lightweight embedding/signature storage (string for v1)
    signature = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("ix_raw_reports_tenant_source", "tenant_id", "source"),
        Index("ix_raw_reports_signature", "signature"),
    )

