"""Add scheduled_reports table.

Revision ID: 2026022503
Revises: 2026022401
Create Date: 2026-02-25 03:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '2026022503'
down_revision = '2026022401'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum type idempotently so a partial deploy retry doesn't fail.
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE reportfrequency AS ENUM ('daily', 'weekly', 'monthly');
        EXCEPTION WHEN duplicate_object THEN
            NULL;
        END $$;
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS scheduled_reports (
            id              SERIAL PRIMARY KEY,
            organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            created_by_id   INTEGER REFERENCES users(id) ON DELETE SET NULL,
            name            VARCHAR(200) NOT NULL,
            frequency       reportfrequency NOT NULL DEFAULT 'weekly',
            recipients      VARCHAR(2000) NOT NULL DEFAULT '',
            is_active       BOOLEAN NOT NULL DEFAULT TRUE,
            include_pipelines BOOLEAN NOT NULL DEFAULT TRUE,
            include_quality   BOOLEAN NOT NULL DEFAULT TRUE,
            last_sent_at    TIMESTAMPTZ,
            next_send_at    TIMESTAMPTZ,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # Indexes — IF NOT EXISTS guards against replay
    op.execute('CREATE INDEX IF NOT EXISTS ix_scheduled_reports_id ON scheduled_reports (id)')
    op.execute('CREATE INDEX IF NOT EXISTS ix_scheduled_reports_organization_id ON scheduled_reports (organization_id)')
    op.execute('CREATE INDEX IF NOT EXISTS ix_scheduled_reports_created_by_id ON scheduled_reports (created_by_id)')
    op.execute('CREATE INDEX IF NOT EXISTS ix_scheduled_reports_next_send_at ON scheduled_reports (next_send_at)')
    op.execute('CREATE INDEX IF NOT EXISTS ix_scheduled_reports_is_active ON scheduled_reports (is_active)')


def downgrade() -> None:
    op.execute('DROP INDEX IF EXISTS ix_scheduled_reports_is_active')
    op.execute('DROP INDEX IF EXISTS ix_scheduled_reports_next_send_at')
    op.execute('DROP INDEX IF EXISTS ix_scheduled_reports_created_by_id')
    op.execute('DROP INDEX IF EXISTS ix_scheduled_reports_organization_id')
    op.execute('DROP INDEX IF EXISTS ix_scheduled_reports_id')
    op.execute('DROP TABLE IF EXISTS scheduled_reports')
    op.execute('DROP TYPE IF EXISTS reportfrequency')
