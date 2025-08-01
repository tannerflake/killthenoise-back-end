from __future__ import annotations

import datetime as dt

from sqlalchemy import Column, DateTime, String

from app.db import Base


class IntegrationToken(Base):
    """Stores OAuth access / refresh tokens per provider (e.g. 'hubspot')."""

    __tablename__ = "integration_tokens"

    provider = Column(String, primary_key=True, nullable=False)
    access_token = Column(String, nullable=False)
    refresh_token = Column(String, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=dt.datetime.utcnow)
    updated_at = Column(
        DateTime(timezone=True), default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow
    )
