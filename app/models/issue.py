from __future__ import annotations

import uuid

from sqlalchemy import Column, DateTime, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.db import Base


class Issue(Base):
    __tablename__ = "issues"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    source = Column(String, nullable=False)
    severity = Column(Integer, nullable=True)
    frequency = Column(Integer, nullable=True)
    status = Column(String, nullable=True)
    type = Column(String, nullable=True)
    tags = Column(String, nullable=True)  # CSV string for now
    jira_issue_key = Column(String, nullable=True)
    hubspot_ticket_id = Column(String, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Composite indexes for common queries
    __table_args__ = (
        Index("ix_issues_tenant_source", "tenant_id", "source"),
        Index("ix_issues_tenant_severity", "tenant_id", "severity"),
        Index("ix_issues_tenant_status", "tenant_id", "status"),
        Index("ix_issues_tenant_created", "tenant_id", "created_at"),
    )
