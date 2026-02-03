"""add webhook_events table

Revision ID: add_webhook_events_001
Revises: add_audit_logs_001
Create Date: 2026-01-25 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = "add_webhook_events_001"
down_revision: Union[str, None] = "add_audit_logs_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "webhook_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("public_id", UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("event_type", sa.String(255), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("signature", sa.String(512), nullable=True),
        sa.Column(
            "status",
            sa.Enum("received", "processed", "failed", name="webhookeventstatus"),
            nullable=False,
            server_default="received",
        ),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_index("ix_webhook_events_id", "webhook_events", ["id"])
    op.create_index("ix_webhook_events_public_id", "webhook_events", ["public_id"], unique=True)
    op.create_index("ix_webhook_events_source_type", "webhook_events", ["source_type"])
    op.create_index("ix_webhook_events_status", "webhook_events", ["status"])
    op.create_index(
        "ix_webhook_events_org_source_created",
        "webhook_events",
        ["organization_id", "source_type", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("webhook_events")
    op.execute("DROP TYPE IF EXISTS webhookeventstatus")
