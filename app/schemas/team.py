from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, UUID4


class TeamBase(BaseModel):
    name: str
    description: Optional[str] = None
    assignment_criteria: str
    is_default_team: bool = False
    display_order: Optional[str] = None


class TeamCreate(BaseModel):
    name: str
    description: Optional[str] = None
    assignment_criteria: str
    is_default_team: bool = False
    display_order: Optional[str] = None


class TeamUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    assignment_criteria: Optional[str] = None
    is_default_team: Optional[bool] = None
    display_order: Optional[str] = None


class Team(TeamBase):
    id: UUID4
    tenant_id: UUID4
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
