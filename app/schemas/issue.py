from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class Issue(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    source: str
    source_id: Optional[str] = None
    severity: Optional[int] = None
    frequency: Optional[int] = None
    status: Optional[str] = None
    type: Optional[str] = None
    tags: Optional[List[str]] = None
    jira_issue_key: Optional[str] = None
    jira_status: Optional[str] = None
    jira_exists: Optional[bool] = None
    ai_type_confidence: Optional[float] = None
    ai_type_reasoning: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True
