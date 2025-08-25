"""Create AI clustering tables

Revision ID: create_ai_clustering_tables
Revises: update_severity_constraint
Create Date: 2025-08-24 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'create_ai_clustering_tables'
down_revision: Union[str, Sequence[str], None] = 'update_severity_constraint'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create AI clustering tables."""
    # Create raw_reports table
    op.create_table('raw_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source', sa.String(), nullable=False),
        sa.Column('external_id', sa.String(), nullable=True),
        sa.Column('url', sa.String(), nullable=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('body', sa.Text(), nullable=True),
        sa.Column('signature', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_raw_reports_tenant_source', 'raw_reports', ['tenant_id', 'source'], unique=False)
    op.create_index('ix_raw_reports_signature', 'raw_reports', ['signature'], unique=False)
    op.create_index(op.f('ix_raw_reports_tenant_id'), 'raw_reports', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_raw_reports_external_id'), 'raw_reports', ['external_id'], unique=False)

    # Create ai_issue_groups table
    op.create_table('ai_issue_groups',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('summary', sa.String(), nullable=True),
        sa.Column('severity', sa.Integer(), nullable=True),
        sa.Column('tags', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('frequency', sa.Integer(), nullable=False, default=1),
        sa.Column('sources', postgresql.JSON(astext_type=sa.Text()), nullable=False, default=list),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_issue_groups_tenant_id'), 'ai_issue_groups', ['tenant_id'], unique=False)

    # Create ai_issue_group_reports table
    op.create_table('ai_issue_group_reports',
        sa.Column('group_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('report_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['group_id'], ['ai_issue_groups.id'], ),
        sa.ForeignKeyConstraint(['report_id'], ['raw_reports.id'], ),
        sa.PrimaryKeyConstraint('group_id', 'report_id')
    )


def downgrade() -> None:
    """Drop AI clustering tables."""
    op.drop_table('ai_issue_group_reports')
    op.drop_index(op.f('ix_ai_issue_groups_tenant_id'), table_name='ai_issue_groups')
    op.drop_table('ai_issue_groups')
    op.drop_index(op.f('ix_raw_reports_external_id'), table_name='raw_reports')
    op.drop_index(op.f('ix_raw_reports_tenant_id'), table_name='raw_reports')
    op.drop_index('ix_raw_reports_signature', table_name='raw_reports')
    op.drop_index('ix_raw_reports_tenant_source', table_name='raw_reports')
    op.drop_table('raw_reports')
