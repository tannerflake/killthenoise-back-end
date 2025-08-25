from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, Float, Index, Integer, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.sql import func

from app.db import Base


class Issue(Base):
    __tablename__ = "issues"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    source = Column(String(100), nullable=False)
    source_id = Column(String(255), nullable=True)
    severity = Column(Integer, nullable=True, default=50, info={'check': 'severity >= 0 AND severity <= 100'})
    frequency = Column(Integer, nullable=True, default=1)
    status = Column(String(50), nullable=True, default='open')
    type = Column(String(20), nullable=True, default='bug')
    tags = Column(ARRAY(Text), nullable=True)
    jira_issue_key = Column(String(50), nullable=True)
    jira_status = Column(String(50), nullable=True)
    jira_exists = Column(Boolean, nullable=True, default=False)
    ai_type_confidence = Column(Float, nullable=True)
    ai_type_reasoning = Column(String, nullable=True)
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Indexes for common queries
    __table_args__ = (
        Index("ix_issues_source", "source"),
        Index("ix_issues_severity", "severity"),
        Index("ix_issues_status", "status"),
        Index("ix_issues_type", "type"),
        Index("ix_issues_created", "created_at"),
        Index("ix_issues_team_id", "team_id"),
    )
