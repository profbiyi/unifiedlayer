"""add_password_reset_fields

Revision ID: 1cecc9e1198c
Revises: fd0b7eb2238c
Create Date: 2026-01-11 07:23:59.560749+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1cecc9e1198c'
down_revision = 'fd0b7eb2238c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add password reset fields to users table
    op.add_column('users', sa.Column('password_reset_token', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('password_reset_expires', sa.DateTime(), nullable=True))


def downgrade() -> None:
    # Remove password reset fields from users table
    op.drop_column('users', 'password_reset_expires')
    op.drop_column('users', 'password_reset_token')
