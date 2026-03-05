"""Add write_mode and schema_contract to pipelines table.

Revision ID: 2026030501
Revises: 2026022503
Create Date: 2026-03-05 00:01:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '2026030501'
down_revision = '2026022503'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types idempotently — if a previous deploy attempt partially ran
    # this migration and was interrupted (e.g. healthcheck timeout), the type may
    # already exist in the production DB.  Using DO $$ BEGIN...EXCEPTION prevents
    # "type already exists" from aborting the migration on a retry.
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE write_mode_enum AS ENUM ('append', 'merge', 'scd2', 'replace');
        EXCEPTION WHEN duplicate_object THEN
            NULL;  -- type already exists, that is fine
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE schema_contract_enum AS ENUM ('evolve', 'freeze', 'discard_columns', 'discard_rows');
        EXCEPTION WHEN duplicate_object THEN
            NULL;
        END $$;
    """)

    # Add columns — use ADD COLUMN IF NOT EXISTS so the migration is safe to
    # replay if it was interrupted after the enum types were created but before
    # the column DDL committed.
    op.execute("""
        ALTER TABLE pipelines
        ADD COLUMN IF NOT EXISTS write_mode write_mode_enum NOT NULL DEFAULT 'merge'
    """)
    op.execute("""
        ALTER TABLE pipelines
        ADD COLUMN IF NOT EXISTS schema_contract schema_contract_enum NOT NULL DEFAULT 'evolve'
    """)


def downgrade() -> None:
    op.execute('ALTER TABLE pipelines DROP COLUMN IF EXISTS schema_contract')
    op.execute('ALTER TABLE pipelines DROP COLUMN IF EXISTS write_mode')
    op.execute('DROP TYPE IF EXISTS write_mode_enum')
    op.execute('DROP TYPE IF EXISTS schema_contract_enum')
