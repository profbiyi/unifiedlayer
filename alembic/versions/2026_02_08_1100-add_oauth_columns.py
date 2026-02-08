"""Add OAuth columns (google_id, oauth_provider) to users table

Revision ID: add_oauth_columns
Revises: super_admin_cross_org
Create Date: 2026-02-08 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_oauth_columns'
down_revision: Union[str, None] = 'super_admin_access_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add Google OAuth columns
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS google_id VARCHAR(255)")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS oauth_provider VARCHAR(50)")
    
    # Create index on google_id for faster lookups
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_google_id ON users (google_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_users_google_id")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS oauth_provider")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS google_id")
