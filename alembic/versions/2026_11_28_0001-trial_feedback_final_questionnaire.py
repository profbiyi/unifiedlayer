"""Align trial_feedback with the final post-trial questionnaire.

Adds the eight-question structure (problem relevance, hardest systems,
biggest concern, continuation likelihood, top feature + reason, local
storage importance, price band), researcher sector/size labels and a
separate consent for quoting anonymised answers. The earlier draft rating
columns become nullable so responses already collected are kept.

Revision ID: 2026112801
Revises: 2026112501
Create Date: 2026-11-28 12:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '2026112801'
down_revision = '2026112501'
branch_labels = None
depends_on = None

NEW_COLUMNS = [
    ("sector_label", "VARCHAR(100)"),
    ("size_label", "VARCHAR(50)"),
    ("problem_relevance", "INTEGER"),
    ("hardest_systems", "TEXT"),
    ("biggest_concern", "TEXT"),
    ("continue_likelihood", "INTEGER"),
    ("top_feature", "VARCHAR(100)"),
    ("top_feature_reason", "TEXT"),
    ("local_storage_importance", "INTEGER"),
    ("price_band", "VARCHAR(50)"),
    ("price_other", "VARCHAR(200)"),
    ("quote_consent", "BOOLEAN NOT NULL DEFAULT FALSE"),
]

RELAXED = [
    "ease_of_use",
    "setup_experience",
    "data_trust",
    "value_rating",
    "adoption_likelihood",
]


def upgrade() -> None:
    for name, ddl in NEW_COLUMNS:
        op.execute(f"ALTER TABLE trial_feedback ADD COLUMN IF NOT EXISTS {name} {ddl}")
    for name in RELAXED:
        op.execute(f"ALTER TABLE trial_feedback ALTER COLUMN {name} DROP NOT NULL")


def downgrade() -> None:
    for name, _ in reversed(NEW_COLUMNS):
        op.execute(f"ALTER TABLE trial_feedback DROP COLUMN IF EXISTS {name}")
