"""Add upsert and insert_only to write_mode_enum (dlt 1.24+).

Revision ID: 2026040301
Revises: 2026030501
Create Date: 2026-04-03 00:01:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '2026040301'
down_revision = '2026030501'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new enum values to write_mode_enum idempotently.
    # PostgreSQL enums cannot be altered inside a transaction block with
    # ADD VALUE, so we use DO $$ blocks with exception handling to be safe
    # on retries (e.g. Railway healthcheck timeout interrupted a prior attempt).
    op.execute("""
        DO $$ BEGIN
            ALTER TYPE write_mode_enum ADD VALUE IF NOT EXISTS 'upsert';
        EXCEPTION WHEN duplicate_object THEN
            NULL;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            ALTER TYPE write_mode_enum ADD VALUE IF NOT EXISTS 'insert_only';
        EXCEPTION WHEN duplicate_object THEN
            NULL;
        END $$;
    """)


def downgrade() -> None:
    # PostgreSQL does not support removing values from an enum type.
    # The values will remain but are harmless if unused.
    pass
