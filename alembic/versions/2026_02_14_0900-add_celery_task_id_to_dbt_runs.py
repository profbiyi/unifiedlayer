"""Add celery_task_id to dbt_runs table

Revision ID: celery_task_id_dbt_runs
Revises: 2026_02_08_1100
Create Date: 2026-02-14 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'celery_task_id_dbt_runs'
down_revision: Union[str, None] = 'add_oauth_columns'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add celery_task_id column to dbt_runs table."""
    # Add the celery_task_id column
    op.add_column(
        'dbt_runs',
        sa.Column('celery_task_id', sa.String(255), nullable=True)
    )

    # Add index for faster lookups by celery_task_id
    op.create_index(
        'ix_dbt_runs_celery_task_id',
        'dbt_runs',
        ['celery_task_id'],
        unique=False
    )


def downgrade() -> None:
    """Remove celery_task_id column from dbt_runs table."""
    # Drop the index first
    op.drop_index('ix_dbt_runs_celery_task_id', table_name='dbt_runs')

    # Drop the column
    op.drop_column('dbt_runs', 'celery_task_id')
