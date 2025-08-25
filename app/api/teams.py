from __future__ import annotations

from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.schemas.team import Team, TeamCreate, TeamUpdate
from app.services.team_service import TeamService

router = APIRouter(prefix="/api/teams", tags=["Teams"])


@router.get("/{tenant_id}")
async def get_teams(
    tenant_id: str,
    session: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get all teams for a tenant."""
    try:
        tenant_uuid = UUID(tenant_id)
        team_service = TeamService(session)
        teams = await team_service.get_teams(tenant_uuid)
        
        data = []
        for team in teams:
            data.append({
                "id": str(team.id),
                "tenant_id": str(team.tenant_id),
                "name": team.name,
                "description": team.description,
                "assignment_criteria": team.assignment_criteria,
                "is_default_team": team.is_default_team,
                "display_order": team.display_order,
                "created_at": team.created_at.isoformat() if team.created_at else None,
                "updated_at": team.updated_at.isoformat() if team.updated_at else None
            })
        
        return {"success": True, "data": data, "count": len(data)}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid tenant ID format")
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/{tenant_id}")
async def create_team(
    tenant_id: str,
    team_data: TeamCreate,
    session: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Create a new team."""
    try:
        tenant_uuid = UUID(tenant_id)
        
        # Check team limit (max 10 teams)
        team_service = TeamService(session)
        existing_teams = await team_service.get_teams(tenant_uuid)
        if len(existing_teams) >= 10:
            raise HTTPException(status_code=400, detail="Maximum of 10 teams allowed")
        
        # Create team data with tenant_id
        team_create_data = TeamCreate(
            name=team_data.name,
            description=team_data.description,
            assignment_criteria=team_data.assignment_criteria,
            is_default_team=team_data.is_default_team,
            display_order=team_data.display_order
        )
        
        team = await team_service.create_team(team_create_data, tenant_uuid)
        
        return {
            "success": True,
            "data": {
                "id": str(team.id),
                "tenant_id": str(team.tenant_id),
                "name": team.name,
                "description": team.description,
                "assignment_criteria": team.assignment_criteria,
                "is_default_team": team.is_default_team,
                "display_order": team.display_order,
                "created_at": team.created_at.isoformat() if team.created_at else None,
                "updated_at": team.updated_at.isoformat() if team.updated_at else None
            },
            "message": "Team created successfully"
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid tenant ID format")
    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.put("/{tenant_id}/{team_id}")
async def update_team(
    tenant_id: str,
    team_id: str,
    team_data: TeamUpdate,
    session: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Update an existing team."""
    try:
        tenant_uuid = UUID(tenant_id)
        team_uuid = UUID(team_id)
        
        team_service = TeamService(session)
        team = await team_service.update_team(team_uuid, tenant_uuid, team_data)
        
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        
        return {
            "success": True,
            "data": {
                "id": str(team.id),
                "tenant_id": str(team.tenant_id),
                "name": team.name,
                "description": team.description,
                "assignment_criteria": team.assignment_criteria,
                "is_default_team": team.is_default_team,
                "display_order": team.display_order,
                "created_at": team.created_at.isoformat() if team.created_at else None,
                "updated_at": team.updated_at.isoformat() if team.updated_at else None
            },
            "message": "Team updated successfully"
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")
    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.delete("/{tenant_id}/{team_id}")
async def delete_team(
    tenant_id: str,
    team_id: str,
    session: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Delete a team."""
    try:
        tenant_uuid = UUID(tenant_id)
        team_uuid = UUID(team_id)
        
        team_service = TeamService(session)
        success = await team_service.delete_team(team_uuid, tenant_uuid)
        
        if not success:
            raise HTTPException(status_code=404, detail="Team not found")
        
        return {
            "success": True,
            "message": "Team deleted successfully"
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")
    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/{tenant_id}/default")
async def get_default_team(
    tenant_id: str,
    session: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get the default team for a tenant."""
    try:
        tenant_uuid = UUID(tenant_id)
        team_service = TeamService(session)
        team = await team_service.get_default_team(tenant_uuid)
        
        if not team:
            return {"success": True, "data": None}
        
        return {
            "success": True,
            "data": {
                "id": str(team.id),
                "tenant_id": str(team.tenant_id),
                "name": team.name,
                "description": team.description,
                "assignment_criteria": team.assignment_criteria,
                "is_default_team": team.is_default_team,
                "display_order": team.display_order,
                "created_at": team.created_at.isoformat() if team.created_at else None,
                "updated_at": team.updated_at.isoformat() if team.updated_at else None
            }
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid tenant ID format")
    except Exception as e:
        return {"success": False, "error": str(e)}
