"""Add scheduled_reports table.

Revision ID: 2026022503
Revises: 2026022401
Create Date: 2026-02-25 03:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '2026022503'
down_revision = '2026022401'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create the ReportFrequency enum type
    op.execute(
        "CREATE TYPE reportfrequency AS ENUM ('daily', 'weekly', 'monthly')"
    )

    op.create_table(
        'scheduled_reports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('created_by_id', sa.Integer(), nullable=True),

        sa.Column('name', sa.String(200), nullable=False),
        sa.Column(
            'frequency',
            postgresql.ENUM('daily', 'weekly', 'monthly', name='reportfrequency', create_type=False),
            nullable=False,
            server_default='weekly',
        ),
        # Comma-separated list of recipient email addresses
        sa.Column('recipients', sa.String(2000), nullable=False, server_default=''),

        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('include_pipelines', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('include_quality', sa.Boolean(), nullable=False, server_default='true'),

        sa.Column('last_sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_send_at', sa.DateTime(timezone=True), nullable=True),

        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),

        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_index('ix_scheduled_reports_id', 'scheduled_reports', ['id'])
    op.create_index('ix_scheduled_reports_organization_id', 'scheduled_reports', ['organization_id'])
    op.create_index('ix_scheduled_reports_created_by_id', 'scheduled_reports', ['created_by_id'])
    op.create_index('ix_scheduled_reports_next_send_at', 'scheduled_reports', ['next_send_at'])
    op.create_index('ix_scheduled_reports_is_active', 'scheduled_reports', ['is_active'])


def downgrade() -> None:
    op.drop_index('ix_scheduled_reports_is_active', table_name='scheduled_reports')
    op.drop_index('ix_scheduled_reports_next_send_at', table_name='scheduled_reports')
    op.drop_index('ix_scheduled_reports_created_by_id', table_name='scheduled_reports')
    op.drop_index('ix_scheduled_reports_organization_id', table_name='scheduled_reports')
    op.drop_index('ix_scheduled_reports_id', table_name='scheduled_reports')
    op.drop_table('scheduled_reports')
    op.execute("DROP TYPE reportfrequency")
