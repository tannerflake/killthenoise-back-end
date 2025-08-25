from __future__ import annotations

import uuid

from sqlalchemy import Column, DateTime, String, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.db import Base


class Team(Base):
    __tablename__ = "teams"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Team information
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Natural language criteria for team assignment
    assignment_criteria = Column(Text, nullable=False)
    
    # Whether this team gets unassigned items by default
    is_default_team = Column(Boolean, nullable=False, default=False)
    
    # Order for display
    display_order = Column(String(10), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
