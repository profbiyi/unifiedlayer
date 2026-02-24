"""Add onboarding progress table.

Revision ID: 2026021702
Revises: 2026021701
Create Date: 2026-02-17 02:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '2026021702'
down_revision = '2026021701'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types
    op.execute("CREATE TYPE userrole AS ENUM ('founder', 'finance', 'operations', 'sales', 'developer', 'other')")
    op.execute("CREATE TYPE onboardingstatus AS ENUM ('not_started', 'in_progress', 'completed', 'skipped')")

    # Create onboarding_progress table
    op.create_table(
        'onboarding_progress',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('business_role', postgresql.ENUM('founder', 'finance', 'operations', 'sales', 'developer', 'other', name='userrole', create_type=False), nullable=True),
        sa.Column('status', postgresql.ENUM('not_started', 'in_progress', 'completed', 'skipped', name='onboardingstatus', create_type=False), server_default='not_started', nullable=True),
        sa.Column('role_selected', sa.Boolean(), server_default='false', nullable=True),
        sa.Column('first_source_connected', sa.Boolean(), server_default='false', nullable=True),
        sa.Column('first_destination_connected', sa.Boolean(), server_default='false', nullable=True),
        sa.Column('first_pipeline_created', sa.Boolean(), server_default='false', nullable=True),
        sa.Column('first_pipeline_run', sa.Boolean(), server_default='false', nullable=True),
        sa.Column('dashboard_viewed', sa.Boolean(), server_default='false', nullable=True),
        sa.Column('ai_assistant_used', sa.Boolean(), server_default='false', nullable=True),
        sa.Column('team_member_invited', sa.Boolean(), server_default='false', nullable=True),
        sa.Column('preferred_sources', postgresql.JSON(astext_type=sa.Text()), server_default='[]', nullable=True),
        sa.Column('skip_reason', sa.String(255), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
    )
    op.create_index('ix_onboarding_progress_id', 'onboarding_progress', ['id'])
    op.create_index('ix_onboarding_progress_user_id', 'onboarding_progress', ['user_id'])


def downgrade() -> None:
    op.drop_table('onboarding_progress')
    op.execute("DROP TYPE onboardingstatus")
    op.execute("DROP TYPE userrole")
