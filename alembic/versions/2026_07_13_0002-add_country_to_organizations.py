"""Add country column to organizations.

The organization's country decides its billing currency at onboarding
(purchasing-power pricing — see REGIONAL_PRICING / COUNTRY_CURRENCY in
backend/models/billing.py).

Revision ID: 2026071302
Revises: 2026071301
Create Date: 2026-07-13 20:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '2026071302'
down_revision = '2026071301'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # IF NOT EXISTS guards against replay on a partially-applied deploy
    op.execute('ALTER TABLE organizations ADD COLUMN IF NOT EXISTS country VARCHAR(100)')


def downgrade() -> None:
    op.execute('ALTER TABLE organizations DROP COLUMN IF EXISTS country')
