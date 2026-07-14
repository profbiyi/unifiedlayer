"""Add MONO to sourcetype enum (+ heal enum drift from create_all era).

The sourcetype PostgreSQL enum was created by the initial migration with
only the original 12 values; later source types (GOOGLE_SHEETS through
MTN_MOMO) reached production via create_all + stamp, so no migration ever
added them. This migration adds MONO and also backfills the missing
values idempotently so a fresh-DB migration replay matches the model.

Revision ID: 2026071401
Revises: 2026071302
Create Date: 2026-07-14 09:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '2026071401'
down_revision = '2026071302'
branch_labels = None
depends_on = None

SOURCE_TYPE_VALUES = [
    'GOOGLE_SHEETS',
    'GOCARDLESS',
    'XERO',
    'OPEN_BANKING',
    'HMRC_MTD',
    'FLUTTERWAVE',
    'MTN_MOMO',
    'MONO',
]


def upgrade() -> None:
    for value in SOURCE_TYPE_VALUES:
        op.execute(f"""
            DO $$ BEGIN
                ALTER TYPE sourcetype ADD VALUE IF NOT EXISTS '{value}';
            EXCEPTION WHEN duplicate_object THEN
                NULL;
            END $$;
        """)


def downgrade() -> None:
    # PostgreSQL does not support removing values from an enum type.
    # The values will remain but are harmless if unused.
    pass
