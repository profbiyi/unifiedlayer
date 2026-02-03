"""add_pipeline_scheduling_fields

Revision ID: f1a087695439
Revises: 1cecc9e1198c
Create Date: 2026-01-11 21:19:54.778401+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f1a087695439'
down_revision = '1cecc9e1198c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add scheduling fields to pipelines table
    op.execute("""
        ALTER TABLE pipelines
        ADD COLUMN IF NOT EXISTS schedule_enabled BOOLEAN NOT NULL DEFAULT false;
    """)

    op.execute("""
        ALTER TABLE pipelines
        ADD COLUMN IF NOT EXISTS schedule_timezone VARCHAR(50) DEFAULT 'UTC';
    """)

    op.execute("""
        ALTER TABLE pipelines
        ADD COLUMN IF NOT EXISTS last_scheduled_run TIMESTAMP;
    """)

    op.execute("""
        ALTER TABLE pipelines
        ADD COLUMN IF NOT EXISTS next_scheduled_run TIMESTAMP;
    """)


def downgrade() -> None:
    # Remove scheduling fields from pipelines table
    op.execute("ALTER TABLE pipelines DROP COLUMN IF EXISTS schedule_enabled;")
    op.execute("ALTER TABLE pipelines DROP COLUMN IF EXISTS schedule_timezone;")
    op.execute("ALTER TABLE pipelines DROP COLUMN IF EXISTS last_scheduled_run;")
    op.execute("ALTER TABLE pipelines DROP COLUMN IF EXISTS next_scheduled_run;")
