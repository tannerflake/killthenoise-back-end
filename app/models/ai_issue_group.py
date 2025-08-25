from __future__ import annotations

import uuid

from sqlalchemy import Column, DateTime, Float, Integer, JSON, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.db import Base


class AIIssueGroup(Base):
    __tablename__ = "ai_issue_groups"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Canonicalized group info
    title = Column(String, nullable=False)
    summary = Column(String, nullable=True)
    severity = Column(Integer, nullable=True)
    tags = Column(String, nullable=True)
    status = Column(String, nullable=True)

    # Roll-up
    frequency = Column(Integer, nullable=False, default=1)
    sources = Column(JSON, nullable=False, default=list)  # e.g., [{source, count}]

    # Optional quality/AI fields
    confidence = Column(Float, nullable=True)
    
    # Team assignment
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=True)

    last_seen_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

