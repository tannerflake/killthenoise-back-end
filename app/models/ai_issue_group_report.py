from __future__ import annotations

from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.db import Base


class AIIssueGroupReport(Base):
    __tablename__ = "ai_issue_group_reports"

    group_id = Column(UUID(as_uuid=True), ForeignKey("ai_issue_groups.id"), primary_key=True)
    report_id = Column(UUID(as_uuid=True), ForeignKey("raw_reports.id"), primary_key=True)

