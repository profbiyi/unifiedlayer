"""Add resource health and health check log tables.

Revision ID: 2026022401
Revises: 2026022001
Create Date: 2026-02-24 00:01:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '2026022401'
down_revision = '2026022001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types
    op.execute("CREATE TYPE healthstatus AS ENUM ('healthy', 'warning', 'critical', 'unknown')")
    op.execute("CREATE TYPE resourcetype AS ENUM ('source', 'pipeline', 'destination')")

    # Create resource_health table (latest health snapshot per resource)
    op.create_table(
        'resource_health',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('public_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),

        # Resource identification
        sa.Column('resource_type', postgresql.ENUM('source', 'pipeline', 'destination', name='resourcetype', create_type=False), nullable=False),
        sa.Column('resource_id', sa.Integer(), nullable=False),

        # Health status
        sa.Column('status', postgresql.ENUM('healthy', 'warning', 'critical', 'unknown', name='healthstatus', create_type=False), nullable=False, server_default='unknown'),
        sa.Column('score', sa.Float(), nullable=False, server_default='0.0'),

        # Check timestamps
        sa.Column('last_checked_at', sa.DateTime(), nullable=True),
        sa.Column('next_check_at', sa.DateTime(), nullable=True),

        # Health details
        sa.Column('issues', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('metrics', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),

        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),

        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('public_id'),
    )
    op.create_index('ix_resource_health_id', 'resource_health', ['id'])
    op.create_index('ix_resource_health_public_id', 'resource_health', ['public_id'])
    op.create_index('ix_resource_health_org_id', 'resource_health', ['organization_id'])
    op.create_index('ix_resource_health_resource_type', 'resource_health', ['resource_type'])
    op.create_index('ix_resource_health_status', 'resource_health', ['status'])
    op.create_index(
        'ix_resource_health_org_type_resource',
        'resource_health',
        ['organization_id', 'resource_type', 'resource_id'],
    )

    # Create health_check_logs table (historical check records)
    op.create_table(
        'health_check_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),

        # Resource identification
        sa.Column('resource_type', postgresql.ENUM('source', 'pipeline', 'destination', name='resourcetype', create_type=False), nullable=False),
        sa.Column('resource_id', sa.Integer(), nullable=False),

        # Health check result
        sa.Column('status', postgresql.ENUM('healthy', 'warning', 'critical', 'unknown', name='healthstatus', create_type=False), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('issues', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('metrics', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),

        # Check metadata
        sa.Column('check_type', sa.String(50), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),

        # Timestamp
        sa.Column('checked_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),

        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_health_check_logs_id', 'health_check_logs', ['id'])
    op.create_index('ix_health_check_logs_org_id', 'health_check_logs', ['organization_id'])
    op.create_index('ix_health_check_logs_resource_type', 'health_check_logs', ['resource_type'])
    op.create_index('ix_health_check_logs_checked_at', 'health_check_logs', ['checked_at'])
    op.create_index(
        'ix_health_log_org_resource_time',
        'health_check_logs',
        ['organization_id', 'resource_type', 'resource_id', 'checked_at'],
    )


def downgrade() -> None:
    # Drop health_check_logs
    op.drop_index('ix_health_log_org_resource_time', table_name='health_check_logs')
    op.drop_index('ix_health_check_logs_checked_at', table_name='health_check_logs')
    op.drop_index('ix_health_check_logs_resource_type', table_name='health_check_logs')
    op.drop_index('ix_health_check_logs_org_id', table_name='health_check_logs')
    op.drop_index('ix_health_check_logs_id', table_name='health_check_logs')
    op.drop_table('health_check_logs')

    # Drop resource_health
    op.drop_index('ix_resource_health_org_type_resource', table_name='resource_health')
    op.drop_index('ix_resource_health_status', table_name='resource_health')
    op.drop_index('ix_resource_health_resource_type', table_name='resource_health')
    op.drop_index('ix_resource_health_org_id', table_name='resource_health')
    op.drop_index('ix_resource_health_public_id', table_name='resource_health')
    op.drop_index('ix_resource_health_id', table_name='resource_health')
    op.drop_table('resource_health')

    # Drop enum types
    op.execute("DROP TYPE resourcetype")
    op.execute("DROP TYPE healthstatus")
