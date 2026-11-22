"""Add onboarded_at / onboarded_organization_id to access_requests.

Marks an access request as having been turned into a real account (org + admin
login) via one-click onboarding, so the admin UI can show "Onboarded" instead of
offering the button again. Distinct from the funnel `status`, which can be set to
trial_active manually without an account existing.

Revision ID: 2026112201
Revises: 2026071601
Create Date: 2026-11-22 10:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '2026112201'
down_revision = '2026071601'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE access_requests "
        "ADD COLUMN IF NOT EXISTS onboarded_at TIMESTAMPTZ"
    )
    op.execute(
        "ALTER TABLE access_requests "
        "ADD COLUMN IF NOT EXISTS onboarded_organization_id INTEGER"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE access_requests DROP COLUMN IF EXISTS onboarded_organization_id")
    op.execute("ALTER TABLE access_requests DROP COLUMN IF EXISTS onboarded_at")
