"""Add missing user columns (email_verification_token, totp_secret, two_factor_enabled, invitation fields)

Revision ID: add_missing_user_columns
Revises: add_notifications_table
Create Date: 2026-02-03 06:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_missing_user_columns'
down_revision: Union[str, None] = 'add_notifications_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add email verification token
    op.add_column('users', sa.Column('email_verification_token', sa.String(255), nullable=True, unique=True))

    # Add email_verified if not exists
    try:
        op.add_column('users', sa.Column('email_verified', sa.Boolean(), nullable=False, server_default='false'))
    except Exception:
        pass  # Column may already exist

    # Add two-factor authentication columns
    op.add_column('users', sa.Column('totp_secret', sa.String(255), nullable=True))
    try:
        op.add_column('users', sa.Column('two_factor_enabled', sa.Boolean(), nullable=False, server_default='false'))
    except Exception:
        pass  # Column may already exist

    # Add invitation fields
    op.add_column('users', sa.Column('invited_by_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True))
    op.add_column('users', sa.Column('invitation_token', sa.String(255), nullable=True, unique=True))
    op.add_column('users', sa.Column('invitation_status', sa.String(20), nullable=True))
    op.add_column('users', sa.Column('invitation_accepted_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('invitation_expires_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'invitation_expires_at')
    op.drop_column('users', 'invitation_accepted_at')
    op.drop_column('users', 'invitation_status')
    op.drop_column('users', 'invitation_token')
    op.drop_column('users', 'invited_by_id')
    op.drop_column('users', 'two_factor_enabled')
    op.drop_column('users', 'totp_secret')
    op.drop_column('users', 'email_verified')
    op.drop_column('users', 'email_verification_token')
