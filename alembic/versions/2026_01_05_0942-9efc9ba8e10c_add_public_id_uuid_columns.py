"""add_public_id_uuid_columns

Revision ID: 9efc9ba8e10c
Revises: 9f448f174994
Create Date: 2026-01-05 09:42:28.489075+00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
import uuid


# revision identifiers, used by Alembic.
revision = '9efc9ba8e10c'
down_revision = '9f448f174994'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add public_id UUID columns to all tables
    tables = ['organizations', 'users', 'data_sources', 'destinations', 'pipelines', 'pipeline_runs']

    for table in tables:
        # Add column as nullable first
        op.add_column(table, sa.Column('public_id', UUID(as_uuid=True), nullable=True))

        # Generate UUIDs for existing rows
        connection = op.get_bind()
        connection.execute(sa.text(f"UPDATE {table} SET public_id = gen_random_uuid() WHERE public_id IS NULL"))

        # Make column not nullable
        op.alter_column(table, 'public_id', nullable=False)

        # Add unique constraint and index
        op.create_unique_constraint(f'{table}_public_id_key', table, ['public_id'])
        op.create_index(f'ix_{table}_public_id', table, ['public_id'])


def downgrade() -> None:
    # Remove public_id columns
    tables = ['organizations', 'users', 'data_sources', 'destinations', 'pipelines', 'pipeline_runs']

    for table in tables:
        op.drop_index(f'ix_{table}_public_id', table_name=table)
        op.drop_constraint(f'{table}_public_id_key', table, type_='unique')
        op.drop_column(table, 'public_id')
