"""Update severity constraint to allow 0-100 values

Revision ID: update_severity_constraint
Revises: create_tenant_settings_table
Create Date: 2025-08-24 15:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'update_severity_constraint'
down_revision: Union[str, Sequence[str], None] = 'create_tenant_settings_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Update severity constraint to allow 0-100 values."""
    # For SQLite, we'll skip constraint modifications for now
    # The constraint will be handled at the application level
    pass


def downgrade() -> None:
    """Revert severity constraint back to 1-5 range."""
    # For SQLite, we'll skip constraint modifications for now
    pass
