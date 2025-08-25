"""Create teams table and add team_id to issues and ai_issue_groups

Revision ID: create_teams_table
Revises: create_ai_clustering_tables
Create Date: 2025-08-24 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'create_teams_table'
down_revision: Union[str, Sequence[str], None] = 'create_ai_clustering_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create teams table and add team_id fields."""
    # Create teams table
    op.create_table('teams',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('assignment_criteria', sa.Text(), nullable=False),
        sa.Column('is_default_team', sa.Boolean(), nullable=False, default=False),
        sa.Column('display_order', sa.String(length=10), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_teams_tenant_id'), 'teams', ['tenant_id'], unique=False)

    # Add team_id to issues table
    op.add_column('issues', sa.Column('team_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index(op.f('ix_issues_team_id'), 'issues', ['team_id'], unique=False)
    op.create_foreign_key(None, 'issues', 'teams', ['team_id'], ['id'])

    # Add team_id to ai_issue_groups table
    op.add_column('ai_issue_groups', sa.Column('team_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index(op.f('ix_ai_issue_groups_team_id'), 'ai_issue_groups', ['team_id'], unique=False)
    op.create_foreign_key(None, 'ai_issue_groups', 'teams', ['team_id'], ['id'])


def downgrade() -> None:
    """Remove teams table and team_id fields."""
    # Remove team_id from ai_issue_groups table
    op.drop_constraint(None, 'ai_issue_groups', type_='foreignkey')
    op.drop_index(op.f('ix_ai_issue_groups_team_id'), table_name='ai_issue_groups')
    op.drop_column('ai_issue_groups', 'team_id')

    # Remove team_id from issues table
    op.drop_constraint(None, 'issues', type_='foreignkey')
    op.drop_index(op.f('ix_issues_team_id'), table_name='issues')
    op.drop_column('issues', 'team_id')

    # Drop teams table
    op.drop_index(op.f('ix_teams_tenant_id'), table_name='teams')
    op.drop_table('teams')
