"""Add super admin cross-org access tables

Revision ID: super_admin_access_001
Revises:
Create Date: 2026-02-07

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'super_admin_access_001'
down_revision = None  # Update this to your latest migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create super_admin_access_logs table
    op.create_table(
        'super_admin_access_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('public_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('super_admin_id', sa.Integer(), nullable=False),
        sa.Column('target_org_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=False),
        sa.Column('resource_id', sa.String(255), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['super_admin_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['target_org_id'], ['organizations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_super_admin_access_logs_public_id', 'super_admin_access_logs', ['public_id'], unique=True)
    op.create_index('ix_super_admin_access_admin_created', 'super_admin_access_logs', ['super_admin_id', 'created_at'])
    op.create_index('ix_super_admin_access_target_created', 'super_admin_access_logs', ['target_org_id', 'created_at'])

    # Create impersonation_sessions table
    op.create_table(
        'impersonation_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('public_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('super_admin_id', sa.Integer(), nullable=False),
        sa.Column('target_org_id', sa.Integer(), nullable=False),
        sa.Column('token_hash', sa.String(255), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('ended_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.ForeignKeyConstraint(['super_admin_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['target_org_id'], ['organizations.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash')
    )
    op.create_index('ix_impersonation_sessions_public_id', 'impersonation_sessions', ['public_id'], unique=True)
    op.create_index('ix_impersonation_session_admin', 'impersonation_sessions', ['super_admin_id', 'is_active'])


def downgrade() -> None:
    op.drop_index('ix_impersonation_session_admin', table_name='impersonation_sessions')
    op.drop_index('ix_impersonation_sessions_public_id', table_name='impersonation_sessions')
    op.drop_table('impersonation_sessions')

    op.drop_index('ix_super_admin_access_target_created', table_name='super_admin_access_logs')
    op.drop_index('ix_super_admin_access_admin_created', table_name='super_admin_access_logs')
    op.drop_index('ix_super_admin_access_logs_public_id', table_name='super_admin_access_logs')
    op.drop_table('super_admin_access_logs')
