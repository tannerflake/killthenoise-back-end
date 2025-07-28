from __future__ import annotations

from typing import Dict

from fastapi import APIRouter

router = APIRouter(prefix="/api/integrations", tags=["Integrations"])


@router.post("/test")
async def integrations_test() -> Dict[str, bool]:
    """Return 200 OK when DB and external credentials are healthy (stubbed)."""
    return {"success": True} 