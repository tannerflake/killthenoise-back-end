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
    # Drop the existing constraint
    op.drop_constraint('issues_severity_check', 'issues', type_='check')
    
    # Add new constraint for 0-100 range
    op.create_check_constraint(
        'issues_severity_check',
        'issues',
        'severity >= 0 AND severity <= 100'
    )


def downgrade() -> None:
    """Revert severity constraint back to 1-5 range."""
    # Drop the new constraint
    op.drop_constraint('issues_severity_check', 'issues', type_='check')
    
    # Add back the old constraint for 1-5 range
    op.create_check_constraint(
        'issues_severity_check',
        'issues',
        'severity >= 1 AND severity <= 5'
    )
