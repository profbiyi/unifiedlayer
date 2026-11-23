"""make ON DELETE SET NULL fk columns nullable (fix org delete drift, part 2)

After 2026112301 fixed the FK ondelete rules, org force-delete hit a second
drift: columns declared ``nullable=True`` + ``ondelete="SET NULL"`` in the
models are still NOT NULL in the live DB (created NOT NULL under the old
create_all() path; the model was relaxed later but no migration altered the
column). So the DB's ON DELETE SET NULL fails with e.g.

    NotNullViolation: null value in column "target_org_id"
    of relation "super_admin_access_logs" violates not-null constraint

This migration drops the NOT NULL on every FK column that the models declare
as ON DELETE SET NULL, so the SET NULL can actually happen on parent delete.
Idempotent (DROP NOT NULL on an already-nullable column is a no-op) and
guarded against missing tables/columns. No-op on SQLite.

Revision ID: 2026112302
Revises: 2026112301
Create Date: 2026-11-23
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '2026112302'
down_revision = '2026112301'
branch_labels = None
depends_on = None


# (table, column) for every FK the models declare ON DELETE SET NULL.
SET_NULL_COLUMNS = [
    ('audit_logs', 'organization_id'),
    ('audit_logs', 'user_id'),
    ('column_lineage', 'dbt_run_id'),
    ('dbt_runs', 'pipeline_run_id'),
    ('generated_models', 'materialized_by_id'),
    ('model_generations', 'pipeline_run_id'),
    ('pipeline_runs', 'original_run_id'),
    ('scheduled_reports', 'created_by_id'),
    ('super_admin_access_logs', 'super_admin_id'),
    ('super_admin_access_logs', 'target_org_id'),
    ('user_invitations', 'invited_by_id'),
    ('user_roles', 'assigned_by_id'),
    ('users', 'invited_by_id'),
]


def _column_exists(conn, table, column):
    return conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = :c"
        ),
        {"t": table, "c": column},
    ).first() is not None


def upgrade():
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return  # SQLite (tests) builds columns from the models already
    for table, column in SET_NULL_COLUMNS:
        if _column_exists(conn, table, column):
            op.execute(f'ALTER TABLE "{table}" ALTER COLUMN "{column}" DROP NOT NULL')


def downgrade():
    # Re-adding NOT NULL could fail on rows already null'd; intentional no-op.
    pass
