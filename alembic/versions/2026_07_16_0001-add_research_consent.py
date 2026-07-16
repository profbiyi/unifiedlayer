"""Add research_consent to access_requests.

Stage-1 informed consent for the DBA Phase 2 research pilot: the
applicant confirms they read the participant information notice and
agree to be contacted about the study.

Revision ID: 2026071601
Revises: 2026071401
Create Date: 2026-07-16 14:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '2026071601'
down_revision = '2026071401'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE access_requests "
        "ADD COLUMN IF NOT EXISTS research_consent BOOLEAN NOT NULL DEFAULT FALSE"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE access_requests DROP COLUMN IF EXISTS research_consent")
