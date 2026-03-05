"""Add write_mode and schema_contract to pipelines table.

Revision ID: 2026030501
Revises: 2026022503
Create Date: 2026-03-05 00:01:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '2026030501'
down_revision = '2026022503'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types first
    op.execute(
        "CREATE TYPE \"writemodeEnum\" AS ENUM ('append', 'merge', 'scd2', 'replace')"
    )
    op.execute(
        "CREATE TYPE \"schemaContractEnum\" AS ENUM ('evolve', 'freeze', 'discard_columns', 'discard_rows')"
    )

    op.add_column(
        'pipelines',
        sa.Column(
            'write_mode',
            postgresql.ENUM(
                'append', 'merge', 'scd2', 'replace',
                name='writemodeEnum',
                create_type=False,
            ),
            nullable=False,
            server_default='merge',
        ),
    )
    op.add_column(
        'pipelines',
        sa.Column(
            'schema_contract',
            postgresql.ENUM(
                'evolve', 'freeze', 'discard_columns', 'discard_rows',
                name='schemaContractEnum',
                create_type=False,
            ),
            nullable=False,
            server_default='evolve',
        ),
    )


def downgrade() -> None:
    op.drop_column('pipelines', 'schema_contract')
    op.drop_column('pipelines', 'write_mode')
    op.execute('DROP TYPE IF EXISTS "writemodeEnum"')
    op.execute('DROP TYPE IF EXISTS "schemaContractEnum"')
