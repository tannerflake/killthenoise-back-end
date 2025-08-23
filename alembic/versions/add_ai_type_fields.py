"""Add AI type confidence and reasoning fields

Revision ID: add_ai_type_fields
Revises: 9435a4f03b05
Create Date: 2025-08-23 19:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'add_ai_type_fields'
down_revision: Union[str, Sequence[str], None] = '9435a4f03b05'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add AI type confidence and reasoning fields to issues table."""
    op.add_column('issues', sa.Column('ai_type_confidence', sa.Float(), nullable=True))
    op.add_column('issues', sa.Column('ai_type_reasoning', sa.String(), nullable=True))


def downgrade() -> None:
    """Remove AI type confidence and reasoning fields from issues table."""
    op.drop_column('issues', 'ai_type_reasoning')
    op.drop_column('issues', 'ai_type_confidence')
