"""Add access_requests table.

Revision ID: 2026071301
Revises: 2026040301
Create Date: 2026-07-13 18:30:00.000000

Note: originally chained onto 2026030501, which forked the migration tree
(2026040301 also descends from it) and made `alembic upgrade head` fail
with multiple heads — blocking backend deploys. Re-parented onto
2026040301 to restore a linear chain.
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '2026071301'
down_revision = '2026040301'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum type idempotently so a partial deploy retry doesn't fail.
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE access_request_status_enum AS ENUM (
                'NEW', 'CONTACTED', 'DISCOVERY_SCHEDULED', 'QUALIFIED', 'TRIAL_ACTIVE', 'DECLINED'
            );
        EXCEPTION WHEN duplicate_object THEN
            NULL;
        END $$;
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS access_requests (
            id              SERIAL PRIMARY KEY,
            company_name    VARCHAR(200) NOT NULL,
            contact_name    VARCHAR(200) NOT NULL,
            email           VARCHAR(255) NOT NULL,
            country         VARCHAR(100) NOT NULL,
            sector          VARCHAR(100) NOT NULL,
            company_size    VARCHAR(50),
            digital_systems JSON,
            data_problem    TEXT NOT NULL,
            status          access_request_status_enum NOT NULL DEFAULT 'NEW',
            notes           TEXT,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # Indexes — IF NOT EXISTS guards against replay
    op.execute('CREATE INDEX IF NOT EXISTS ix_access_requests_id ON access_requests (id)')
    op.execute('CREATE INDEX IF NOT EXISTS ix_access_requests_email ON access_requests (email)')
    op.execute('CREATE INDEX IF NOT EXISTS ix_access_requests_status ON access_requests (status)')
    op.execute('CREATE INDEX IF NOT EXISTS ix_access_requests_created_at ON access_requests (created_at)')


def downgrade() -> None:
    op.execute('DROP INDEX IF EXISTS ix_access_requests_created_at')
    op.execute('DROP INDEX IF EXISTS ix_access_requests_status')
    op.execute('DROP INDEX IF EXISTS ix_access_requests_email')
    op.execute('DROP INDEX IF EXISTS ix_access_requests_id')
    op.execute('DROP TABLE IF EXISTS access_requests')
    op.execute('DROP TYPE IF EXISTS access_request_status_enum')
