"""Add AI conversation tables.

Revision ID: 2026021701
Revises: 2026_02_16_1700
Create Date: 2026-02-17 01:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '2026021701'
down_revision = 'add_column_lineage'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types
    op.execute("CREATE TYPE messagerole AS ENUM ('user', 'assistant', 'system')")
    op.execute("CREATE TYPE charttype AS ENUM ('line', 'bar', 'pie', 'number', 'table')")

    # Create ai_conversations table
    op.create_table(
        'ai_conversations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_ai_conversations_id', 'ai_conversations', ['id'])
    op.create_index('ix_ai_conversations_org_user', 'ai_conversations', ['organization_id', 'user_id'])
    op.create_index('ix_ai_conversations_updated', 'ai_conversations', ['updated_at'])

    # Create ai_messages table
    op.create_table(
        'ai_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('conversation_id', sa.Integer(), nullable=False),
        sa.Column('role', postgresql.ENUM('user', 'assistant', 'system', name='messagerole', create_type=False), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('sql', sa.Text(), nullable=True),
        sa.Column('results_json', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('row_count', sa.Integer(), nullable=True),
        sa.Column('chart_type', postgresql.ENUM('line', 'bar', 'pie', 'number', 'table', name='charttype', create_type=False), nullable=True),
        sa.Column('chart_config', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('execution_time_ms', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['conversation_id'], ['ai_conversations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_ai_messages_id', 'ai_messages', ['id'])
    op.create_index('ix_ai_messages_conversation', 'ai_messages', ['conversation_id'])

    # Create ai_suggested_questions table
    op.create_table(
        'ai_suggested_questions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('question', sa.String(500), nullable=False),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('source_types', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('priority', sa.Integer(), default=0, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_ai_suggested_questions_id', 'ai_suggested_questions', ['id'])
    op.create_index('ix_ai_suggested_category', 'ai_suggested_questions', ['category'])


def downgrade() -> None:
    op.drop_table('ai_suggested_questions')
    op.drop_table('ai_messages')
    op.drop_table('ai_conversations')
    op.execute("DROP TYPE charttype")
    op.execute("DROP TYPE messagerole")
