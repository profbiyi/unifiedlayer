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
    # If the prior migration (2026030501) was stamped but not actually executed
    # (e.g. the DB was bootstrapped with create_all() before the write_mode column
    # was in the model, then alembic stamp head was run), the enum type and columns
    # may be missing.  Create them idempotently first, then add the new values.

    # 1. Ensure the enum types exist (may have been created by 2026030501 or create_all())
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE write_mode_enum AS ENUM ('append', 'merge', 'scd2', 'replace');
        EXCEPTION WHEN duplicate_object THEN
            NULL;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE schema_contract_enum AS ENUM ('evolve', 'freeze', 'discard_columns', 'discard_rows');
        EXCEPTION WHEN duplicate_object THEN
            NULL;
        END $$;
    """)

    # 2. Ensure the columns exist on the pipelines table
    op.execute("""
        ALTER TABLE pipelines
        ADD COLUMN IF NOT EXISTS write_mode write_mode_enum NOT NULL DEFAULT 'merge'
    """)
    op.execute("""
        ALTER TABLE pipelines
        ADD COLUMN IF NOT EXISTS schema_contract schema_contract_enum NOT NULL DEFAULT 'evolve'
    """)

    # 3. Add new enum values (dlt 1.24+ write strategies)
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
