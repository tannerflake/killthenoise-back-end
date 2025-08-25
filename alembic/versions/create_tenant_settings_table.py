"""Create tenant_settings table

Revision ID: create_tenant_settings_table
Revises: add_ai_type_fields
Create Date: 2025-08-23 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'create_tenant_settings_table'
down_revision: Union[str, Sequence[str], None] = 'add_ai_type_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create tenant_settings table."""
    op.create_table('tenant_settings',
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('grouping_instructions', sa.Text(), nullable=True),
        sa.Column('type_classification_instructions', sa.Text(), nullable=True),
        sa.Column('severity_calculation_instructions', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('tenant_id')
    )


def downgrade() -> None:
    """Drop tenant_settings table."""
    op.drop_table('tenant_settings')
