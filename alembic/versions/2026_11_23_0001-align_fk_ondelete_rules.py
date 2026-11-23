"""align FK ondelete rules with models (fix org delete cascade drift)

Production FK constraints were originally created by create_all() before the
models declared ``ondelete="CASCADE"``, so they are ON DELETE NO ACTION in the
live DB. That makes deleting an organization fail with ForeignKeyViolation
(e.g. subscriptions_organization_id_fkey). This migration recreates every FK
that declares an ondelete rule so the database matches the models.

It is idempotent and safe: for each (table, column, parent) it drops whatever
FK constraint currently exists on that column and recreates it with the
declared ON DELETE rule. Guarded so a missing table/column is skipped.

Revision ID: 2026112301
Revises: 2026112201
Create Date: 2026-11-23
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '2026112301'
down_revision = '2026112201'
branch_labels = None
depends_on = None


# (child_table, child_column, parent_table, parent_column, ondelete)
FKS = [
    ('ai_conversations', 'organization_id', 'organizations', 'id', 'CASCADE'),
    ('ai_conversations', 'user_id', 'users', 'id', 'CASCADE'),
    ('ai_messages', 'conversation_id', 'ai_conversations', 'id', 'CASCADE'),
    ('api_keys', 'organization_id', 'organizations', 'id', 'CASCADE'),
    ('api_keys', 'user_id', 'users', 'id', 'CASCADE'),
    ('audit_logs', 'organization_id', 'organizations', 'id', 'SET NULL'),
    ('audit_logs', 'user_id', 'users', 'id', 'SET NULL'),
    ('column_lineage', 'dbt_run_id', 'dbt_runs', 'id', 'SET NULL'),
    ('column_lineage', 'organization_id', 'organizations', 'id', 'CASCADE'),
    ('column_lineage', 'pipeline_id', 'pipelines', 'id', 'CASCADE'),
    ('column_lineage', 'transformation_id', 'sql_transformations', 'id', 'CASCADE'),
    ('data_sources', 'organization_id', 'organizations', 'id', 'CASCADE'),
    ('dbt_column_metadata', 'dbt_project_id', 'dbt_projects', 'id', 'CASCADE'),
    ('dbt_projects', 'organization_id', 'organizations', 'id', 'CASCADE'),
    ('dbt_runs', 'dbt_project_id', 'dbt_projects', 'id', 'CASCADE'),
    ('dbt_runs', 'pipeline_run_id', 'pipeline_runs', 'id', 'SET NULL'),
    ('destinations', 'organization_id', 'organizations', 'id', 'CASCADE'),
    ('generated_models', 'materialized_by_id', 'users', 'id', 'SET NULL'),
    ('generated_models', 'organization_id', 'organizations', 'id', 'CASCADE'),
    ('generated_models', 'pipeline_id', 'pipelines', 'id', 'CASCADE'),
    ('health_check_logs', 'organization_id', 'organizations', 'id', 'CASCADE'),
    ('impersonation_sessions', 'super_admin_id', 'users', 'id', 'CASCADE'),
    ('impersonation_sessions', 'target_org_id', 'organizations', 'id', 'CASCADE'),
    ('invoices', 'organization_id', 'organizations', 'id', 'CASCADE'),
    ('invoices', 'subscription_id', 'subscriptions', 'id', 'CASCADE'),
    ('lineage_edges', 'source_node_id', 'lineage_nodes', 'id', 'CASCADE'),
    ('lineage_edges', 'target_node_id', 'lineage_nodes', 'id', 'CASCADE'),
    ('model_generations', 'organization_id', 'organizations', 'id', 'CASCADE'),
    ('model_generations', 'pipeline_id', 'pipelines', 'id', 'CASCADE'),
    ('model_generations', 'pipeline_run_id', 'pipeline_runs', 'id', 'SET NULL'),
    ('notifications', 'organization_id', 'organizations', 'id', 'CASCADE'),
    ('notifications', 'user_id', 'users', 'id', 'CASCADE'),
    ('onboarding_progress', 'organization_id', 'organizations', 'id', 'CASCADE'),
    ('onboarding_progress', 'user_id', 'users', 'id', 'CASCADE'),
    ('pipeline_dbt_configs', 'dbt_project_id', 'dbt_projects', 'id', 'CASCADE'),
    ('pipeline_dbt_configs', 'pipeline_id', 'pipelines', 'id', 'CASCADE'),
    ('pipeline_quality_checks', 'pipeline_id', 'pipelines', 'id', 'CASCADE'),
    ('pipeline_quality_checks', 'quality_check_id', 'quality_checks', 'id', 'CASCADE'),
    ('pipeline_runs', 'original_run_id', 'pipeline_runs', 'id', 'SET NULL'),
    ('pipeline_runs', 'pipeline_id', 'pipelines', 'id', 'CASCADE'),
    ('pipelines', 'destination_id', 'destinations', 'id', 'CASCADE'),
    ('pipelines', 'organization_id', 'organizations', 'id', 'CASCADE'),
    ('pipelines', 'source_id', 'data_sources', 'id', 'CASCADE'),
    ('quality_check_results', 'pipeline_check_id', 'pipeline_quality_checks', 'id', 'CASCADE'),
    ('quality_check_results', 'pipeline_run_id', 'pipeline_runs', 'id', 'CASCADE'),
    ('quality_checks', 'organization_id', 'organizations', 'id', 'CASCADE'),
    ('resource_health', 'organization_id', 'organizations', 'id', 'CASCADE'),
    ('role_permissions', 'permission_id', 'permissions', 'id', 'CASCADE'),
    ('role_permissions', 'role_id', 'roles', 'id', 'CASCADE'),
    ('scheduled_reports', 'created_by_id', 'users', 'id', 'SET NULL'),
    ('scheduled_reports', 'organization_id', 'organizations', 'id', 'CASCADE'),
    ('sql_transformations', 'pipeline_id', 'pipelines', 'id', 'CASCADE'),
    ('subscriptions', 'organization_id', 'organizations', 'id', 'CASCADE'),
    ('super_admin_access_logs', 'super_admin_id', 'users', 'id', 'SET NULL'),
    ('super_admin_access_logs', 'target_org_id', 'organizations', 'id', 'SET NULL'),
    ('transformation_results', 'pipeline_run_id', 'pipeline_runs', 'id', 'CASCADE'),
    ('transformation_results', 'transformation_id', 'sql_transformations', 'id', 'CASCADE'),
    ('usage_records', 'organization_id', 'organizations', 'id', 'CASCADE'),
    ('user_invitations', 'invited_by_id', 'users', 'id', 'SET NULL'),
    ('user_invitations', 'organization_id', 'organizations', 'id', 'CASCADE'),
    ('user_invitations', 'role_id', 'roles', 'id', 'CASCADE'),
    ('user_roles', 'assigned_by_id', 'users', 'id', 'SET NULL'),
    ('user_roles', 'organization_id', 'organizations', 'id', 'CASCADE'),
    ('user_roles', 'role_id', 'roles', 'id', 'CASCADE'),
    ('user_roles', 'user_id', 'users', 'id', 'CASCADE'),
    ('users', 'invited_by_id', 'users', 'id', 'SET NULL'),
    ('users', 'organization_id', 'organizations', 'id', 'CASCADE'),
    ('webhook_events', 'organization_id', 'organizations', 'id', 'CASCADE'),
]


def _column_exists(conn, table, column):
    return conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = :c"
        ),
        {"t": table, "c": column},
    ).first() is not None


def _existing_fk_names(conn, table, column, parent):
    rows = conn.execute(
        sa.text(
            """
            SELECT con.conname
            FROM pg_constraint con
            JOIN pg_class rel  ON rel.oid = con.conrelid
            JOIN pg_class refc ON refc.oid = con.confrelid
            JOIN pg_attribute att ON att.attrelid = con.conrelid
                                 AND att.attnum = ANY(con.conkey)
            WHERE con.contype = 'f'
              AND rel.relname  = :t
              AND att.attname  = :c
              AND refc.relname = :p
              AND array_length(con.conkey, 1) = 1
            """
        ),
        {"t": table, "c": column, "p": parent},
    ).fetchall()
    return [r[0] for r in rows]


def upgrade():
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return  # SQLite (tests) already builds constraints from the models
    for table, column, parent, parent_col, ondelete in FKS:
        if not _column_exists(conn, table, column):
            continue
        for name in _existing_fk_names(conn, table, column, parent):
            op.execute(f'ALTER TABLE "{table}" DROP CONSTRAINT "{name}"')
        canonical = f"{table}_{column}_fkey"
        op.execute(
            f'ALTER TABLE "{table}" ADD CONSTRAINT "{canonical}" '
            f'FOREIGN KEY ("{column}") REFERENCES "{parent}" ("{parent_col}") '
            f'ON DELETE {ondelete}'
        )


def downgrade():
    # Reverting cascades would re-introduce the delete bug; intentional no-op.
    pass
