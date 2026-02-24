"""Add column lineage tables

Revision ID: add_column_lineage
Revises: 2026_02_14_0900-add_celery_task_id_to_dbt_runs
Create Date: 2026-02-16 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_column_lineage'
down_revision = 'celery_task_id_dbt_runs'
branch_labels = None
depends_on = None


def upgrade():
    # Create column_lineage_type enum
    column_lineage_type = postgresql.ENUM(
        'direct', 'derived', 'aggregated', 'cast', 'filtered', 'joined', 'grouped',
        name='columnlineagetype'
    )
    column_lineage_type.create(op.get_bind(), checkfirst=True)

    # Create column_lineage table
    op.create_table(
        'column_lineage',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('public_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_database', sa.String(255), nullable=True),
        sa.Column('source_schema', sa.String(255), nullable=True),
        sa.Column('source_table', sa.String(255), nullable=False),
        sa.Column('source_column', sa.String(255), nullable=False),
        sa.Column('source_data_type', sa.String(100), nullable=True),
        sa.Column('target_database', sa.String(255), nullable=True),
        sa.Column('target_schema', sa.String(255), nullable=True),
        sa.Column('target_table', sa.String(255), nullable=False),
        sa.Column('target_column', sa.String(255), nullable=False),
        sa.Column('target_data_type', sa.String(100), nullable=True),
        sa.Column('lineage_type', sa.Enum(
            'direct', 'derived', 'aggregated', 'cast', 'filtered', 'joined', 'grouped',
            name='columnlineagetype'
        ), nullable=False, server_default='direct'),
        sa.Column('transformation_expression', sa.Text(), nullable=True),
        sa.Column('transformation_id', sa.Integer(), nullable=True),
        sa.Column('pipeline_id', sa.Integer(), nullable=True),
        sa.Column('dbt_run_id', sa.Integer(), nullable=True),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('confidence_score', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('properties', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['transformation_id'], ['sql_transformations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['pipeline_id'], ['pipelines.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['dbt_run_id'], ['dbt_runs.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('public_id'),
        sa.UniqueConstraint(
            'source_table', 'source_column', 'target_table', 'target_column',
            'transformation_id', 'pipeline_id',
            name='unique_column_lineage'
        )
    )

    # Create indexes
    op.create_index('ix_column_lineage_id', 'column_lineage', ['id'])
    op.create_index('ix_column_lineage_public_id', 'column_lineage', ['public_id'])
    op.create_index('ix_column_lineage_source', 'column_lineage', ['source_table', 'source_column'])
    op.create_index('ix_column_lineage_target', 'column_lineage', ['target_table', 'target_column'])
    op.create_index('ix_column_lineage_pipeline', 'column_lineage', ['pipeline_id'])
    op.create_index('ix_column_lineage_transformation', 'column_lineage', ['transformation_id'])
    op.create_index('ix_column_lineage_organization', 'column_lineage', ['organization_id'])

    # Create dbt_column_metadata table
    op.create_table(
        'dbt_column_metadata',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('dbt_project_id', sa.Integer(), nullable=False),
        sa.Column('model_name', sa.String(255), nullable=False),
        sa.Column('column_name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('data_type', sa.String(100), nullable=True),
        sa.Column('is_nullable', sa.String(10), nullable=True),
        sa.Column('tests', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('tags', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('meta', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('depends_on', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['dbt_project_id'], ['dbt_projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'dbt_project_id', 'model_name', 'column_name',
            name='unique_dbt_column'
        )
    )

    # Create indexes
    op.create_index('ix_dbt_column_metadata_id', 'dbt_column_metadata', ['id'])
    op.create_index('ix_dbt_column_metadata_project', 'dbt_column_metadata', ['dbt_project_id'])
    op.create_index('ix_dbt_column_model', 'dbt_column_metadata', ['model_name'])


def downgrade():
    # Drop dbt_column_metadata table
    op.drop_index('ix_dbt_column_model', table_name='dbt_column_metadata')
    op.drop_index('ix_dbt_column_metadata_project', table_name='dbt_column_metadata')
    op.drop_index('ix_dbt_column_metadata_id', table_name='dbt_column_metadata')
    op.drop_table('dbt_column_metadata')

    # Drop column_lineage table
    op.drop_index('ix_column_lineage_organization', table_name='column_lineage')
    op.drop_index('ix_column_lineage_transformation', table_name='column_lineage')
    op.drop_index('ix_column_lineage_pipeline', table_name='column_lineage')
    op.drop_index('ix_column_lineage_target', table_name='column_lineage')
    op.drop_index('ix_column_lineage_source', table_name='column_lineage')
    op.drop_index('ix_column_lineage_public_id', table_name='column_lineage')
    op.drop_index('ix_column_lineage_id', table_name='column_lineage')
    op.drop_table('column_lineage')

    # Drop enum type
    column_lineage_type = postgresql.ENUM(
        'direct', 'derived', 'aggregated', 'cast', 'filtered', 'joined', 'grouped',
        name='columnlineagetype'
    )
    column_lineage_type.drop(op.get_bind(), checkfirst=True)
