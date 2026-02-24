"""Add generated models table.

Revision ID: 2026022001
Revises: 2026_02_17_0200
Create Date: 2026-02-20 01:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '2026022001'
down_revision = '2026021702'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types
    op.execute("CREATE TYPE modellayer AS ENUM ('raw', 'canonical', 'dimensional')")
    op.execute("CREATE TYPE modelstatus AS ENUM ('draft', 'approved', 'deployed', 'deprecated')")

    # Create generated_models table
    op.create_table(
        'generated_models',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('public_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('pipeline_id', sa.Integer(), nullable=False),

        # Model metadata
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),

        # Classification
        sa.Column('layer', postgresql.ENUM('raw', 'canonical', 'dimensional', name='modellayer', create_type=False), nullable=False),
        sa.Column('model_type', sa.String(50), nullable=False),

        # Source and definition
        sa.Column('source_tables', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('sql_definition', sa.Text(), nullable=False),
        sa.Column('columns', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('relationships', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='[]'),

        # Business context
        sa.Column('business_questions', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('ai_reasoning', sa.Text(), nullable=True),

        # Status and deployment
        sa.Column('status', postgresql.ENUM('draft', 'approved', 'deployed', 'deprecated', name='modelstatus', create_type=False), nullable=False, server_default='draft'),
        sa.Column('is_materialized', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('materialized_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('materialized_by_id', sa.Integer(), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

        # Constraints
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['pipeline_id'], ['pipelines.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['materialized_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('public_id'),
    )

    # Create indexes
    op.create_index('ix_generated_models_id', 'generated_models', ['id'])
    op.create_index('ix_generated_models_public_id', 'generated_models', ['public_id'])
    op.create_index('ix_generated_models_org_id', 'generated_models', ['organization_id'])
    op.create_index('ix_generated_models_pipeline_id', 'generated_models', ['pipeline_id'])
    op.create_index('ix_generated_models_name', 'generated_models', ['name'])
    op.create_index('ix_generated_models_status', 'generated_models', ['status'])
    op.create_index('ix_generated_models_layer', 'generated_models', ['layer'])

    # Create model_generations table for tracking generation runs
    op.create_table(
        'model_generations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('public_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('pipeline_id', sa.Integer(), nullable=False),
        sa.Column('pipeline_run_id', sa.Integer(), nullable=True),

        # Status
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),

        # Results
        sa.Column('models_generated', sa.Integer(), nullable=True),
        sa.Column('questions_generated', sa.Integer(), nullable=True),

        # Error information
        sa.Column('error_message', sa.Text(), nullable=True),

        # Metadata
        sa.Column('schema_tables_analyzed', sa.Integer(), nullable=True),
        sa.Column('schema_columns_analyzed', sa.Integer(), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

        # Constraints
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['pipeline_id'], ['pipelines.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['pipeline_run_id'], ['pipeline_runs.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('public_id'),
    )

    # Create indexes for model_generations
    op.create_index('ix_model_generations_id', 'model_generations', ['id'])
    op.create_index('ix_model_generations_public_id', 'model_generations', ['public_id'])
    op.create_index('ix_model_generations_org_id', 'model_generations', ['organization_id'])
    op.create_index('ix_model_generations_pipeline_id', 'model_generations', ['pipeline_id'])
    op.create_index('ix_model_generations_status', 'model_generations', ['status'])


def downgrade() -> None:
    # Drop model_generations table
    op.drop_index('ix_model_generations_status', table_name='model_generations')
    op.drop_index('ix_model_generations_pipeline_id', table_name='model_generations')
    op.drop_index('ix_model_generations_org_id', table_name='model_generations')
    op.drop_index('ix_model_generations_public_id', table_name='model_generations')
    op.drop_index('ix_model_generations_id', table_name='model_generations')
    op.drop_table('model_generations')

    # Drop generated_models table
    op.drop_index('ix_generated_models_layer', table_name='generated_models')
    op.drop_index('ix_generated_models_status', table_name='generated_models')
    op.drop_index('ix_generated_models_name', table_name='generated_models')
    op.drop_index('ix_generated_models_pipeline_id', table_name='generated_models')
    op.drop_index('ix_generated_models_org_id', table_name='generated_models')
    op.drop_index('ix_generated_models_public_id', table_name='generated_models')
    op.drop_index('ix_generated_models_id', table_name='generated_models')
    op.drop_table('generated_models')

    # Drop enum types
    op.execute("DROP TYPE modelstatus")
    op.execute("DROP TYPE modellayer")
