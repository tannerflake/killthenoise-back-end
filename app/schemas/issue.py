from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, UUID4


class Issue(BaseModel):
    id: UUID4
    title: str
    description: Optional[str] = None
    source: str
    severity: Optional[int] = None
    frequency: Optional[int] = None
    status: Optional[str] = None
    type: Optional[str] = None
    tags: Optional[List[str]] = None
    jira_issue_key: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True 