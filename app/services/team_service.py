from __future__ import annotations

import logging
from typing import Optional, List
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.team import Team
from app.schemas.team import TeamCreate, TeamUpdate

logger = logging.getLogger(__name__)


class TeamService:
    """Service for managing teams and team assignments."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_teams(self, tenant_id: UUID) -> List[Team]:
        """Get all teams for a tenant."""
        stmt = select(Team).where(Team.tenant_id == tenant_id).order_by(Team.display_order, Team.name)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_team(self, team_id: UUID, tenant_id: UUID) -> Optional[Team]:
        """Get a specific team by ID."""
        stmt = select(Team).where(
            and_(Team.id == team_id, Team.tenant_id == tenant_id)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def create_team(self, team_data: TeamCreate, tenant_id: UUID) -> Team:
        """Create a new team."""
        # Check if this would be the first team (make it default)
        existing_teams = await self.get_teams(tenant_id)
        if not existing_teams:
            team_data.is_default_team = True
        
        # If this team is being set as default, unset other defaults
        if team_data.is_default_team:
            await self._unset_other_defaults(tenant_id)
        
        team = Team(
            tenant_id=tenant_id,
            name=team_data.name,
            description=team_data.description,
            assignment_criteria=team_data.assignment_criteria,
            is_default_team=team_data.is_default_team,
            display_order=team_data.display_order
        )
        self.session.add(team)
        await self.session.commit()
        await self.session.refresh(team)
        return team

    async def update_team(self, team_id: UUID, tenant_id: UUID, team_data: TeamUpdate) -> Optional[Team]:
        """Update an existing team."""
        team = await self.get_team(team_id, tenant_id)
        if not team:
            return None
        
        # If this team is being set as default, unset other defaults
        if team_data.is_default_team:
            await self._unset_other_defaults(tenant_id)
        
        # Update fields
        update_data = team_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(team, field, value)
        
        await self.session.commit()
        await self.session.refresh(team)
        return team

    async def delete_team(self, team_id: UUID, tenant_id: UUID) -> bool:
        """Delete a team."""
        team = await self.get_team(team_id, tenant_id)
        if not team:
            return False
        
        # If this is the default team, make another team default
        if team.is_default_team:
            other_teams = await self.get_teams(tenant_id)
            other_teams = [t for t in other_teams if t.id != team_id]
            if other_teams:
                other_teams[0].is_default_team = True
                await self.session.commit()
        
        await self.session.delete(team)
        await self.session.commit()
        return True

    async def get_default_team(self, tenant_id: UUID) -> Optional[Team]:
        """Get the default team for a tenant."""
        stmt = select(Team).where(
            and_(Team.tenant_id == tenant_id, Team.is_default_team == True)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def assign_team_to_issue(self, title: str, description: str, tenant_id: UUID) -> Optional[UUID]:
        """Assign a team to an issue based on natural language criteria."""
        teams = await self.get_teams(tenant_id)
        if not teams:
            return None
        
        # For now, use simple keyword matching
        # In the future, this could be enhanced with AI analysis
        issue_text = f"{title} {description}".lower()
        
        for team in teams:
            if team.assignment_criteria:
                criteria = team.assignment_criteria.lower()
                # Simple keyword matching - could be enhanced with AI
                if any(keyword in issue_text for keyword in criteria.split()):
                    return team.id
        
        # If no team matches, return default team
        default_team = await self.get_default_team(tenant_id)
        return default_team.id if default_team else None

    async def _unset_other_defaults(self, tenant_id: UUID) -> None:
        """Unset default flag for all other teams in the tenant."""
        stmt = select(Team).where(
            and_(Team.tenant_id == tenant_id, Team.is_default_team == True)
        )
        result = await self.session.execute(stmt)
        default_teams = result.scalars().all()
        
        for team in default_teams:
            team.is_default_team = False
        
        await self.session.commit()
