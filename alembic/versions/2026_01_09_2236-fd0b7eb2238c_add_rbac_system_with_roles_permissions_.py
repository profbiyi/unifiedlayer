"""add_rbac_system_with_roles_permissions_and_subscriptions

Revision ID: fd0b7eb2238c
Revises: 9efc9ba8e10c
Create Date: 2026-01-09 22:36:50.129207+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fd0b7eb2238c'
down_revision = '9efc9ba8e10c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create roles table
    op.create_table(
        'roles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('slug', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('scope', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('slug')
    )

    # Create permissions table
    op.create_table(
        'permissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('resource', sa.String(length=50), nullable=False),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('resource', 'action', name='uq_resource_action')
    )

    # Create role_permissions junction table
    op.create_table(
        'role_permissions',
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('permission_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['permission_id'], ['permissions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('role_id', 'permission_id')
    )

    # Create user_roles junction table
    op.create_table(
        'user_roles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=True),
        sa.Column('assigned_by_id', sa.Integer(), nullable=True),
        sa.Column('assigned_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['assigned_by_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'role_id', 'organization_id', name='uq_user_role_org')
    )

    # Create user_invitations table
    op.create_table(
        'user_invitations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('public_id', sa.String(length=36), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('invited_by_id', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(length=255), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('accepted_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=20), server_default='pending', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['invited_by_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('public_id'),
        sa.UniqueConstraint('token')
    )

    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=True),
        sa.Column('resource_id', sa.Integer(), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # Add indexes for performance
    op.create_index('ix_user_roles_user_id', 'user_roles', ['user_id'])
    op.create_index('ix_user_roles_organization_id', 'user_roles', ['organization_id'])
    op.create_index('ix_user_invitations_email', 'user_invitations', ['email'])
    op.create_index('ix_user_invitations_status', 'user_invitations', ['status'])
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_organization_id', 'audit_logs', ['organization_id'])
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])

    # Add subscription fields to organizations table
    op.add_column('organizations', sa.Column('subscription_plan', sa.String(length=20), server_default='starter', nullable=False))
    op.add_column('organizations', sa.Column('max_users', sa.Integer(), server_default='3', nullable=False))
    op.add_column('organizations', sa.Column('subscription_status', sa.String(length=20), server_default='active', nullable=False))
    op.add_column('organizations', sa.Column('trial_ends_at', sa.DateTime(), nullable=True))
    op.add_column('organizations', sa.Column('billing_email', sa.String(length=255), nullable=True))

    # Add invitation-related fields to users table
    op.add_column('users', sa.Column('email_verified', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('users', sa.Column('invited_by_id', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('invitation_accepted_at', sa.DateTime(), nullable=True))
    op.create_foreign_key('fk_users_invited_by', 'users', 'users', ['invited_by_id'], ['id'])


def downgrade() -> None:
    # Drop foreign key from users table
    op.drop_constraint('fk_users_invited_by', 'users', type_='foreignkey')

    # Remove columns from users table
    op.drop_column('users', 'invitation_accepted_at')
    op.drop_column('users', 'invited_by_id')
    op.drop_column('users', 'email_verified')

    # Remove columns from organizations table
    op.drop_column('organizations', 'billing_email')
    op.drop_column('organizations', 'trial_ends_at')
    op.drop_column('organizations', 'subscription_status')
    op.drop_column('organizations', 'max_users')
    op.drop_column('organizations', 'subscription_plan')

    # Drop indexes
    op.drop_index('ix_audit_logs_created_at')
    op.drop_index('ix_audit_logs_organization_id')
    op.drop_index('ix_audit_logs_user_id')
    op.drop_index('ix_user_invitations_status')
    op.drop_index('ix_user_invitations_email')
    op.drop_index('ix_user_roles_organization_id')
    op.drop_index('ix_user_roles_user_id')

    # Drop tables
    op.drop_table('audit_logs')
    op.drop_table('user_invitations')
    op.drop_table('user_roles')
    op.drop_table('role_permissions')
    op.drop_table('permissions')
    op.drop_table('roles')
