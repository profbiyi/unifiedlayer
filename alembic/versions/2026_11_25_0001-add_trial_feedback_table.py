"""Add trial_feedback table (post-trial questionnaire + testimonials).

Revision ID: 2026112501
Revises: 2026112302
Create Date: 2026-11-25 17:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '2026112501'
down_revision = '2026112302'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE testimonial_attribution_enum AS ENUM (
                'FULL', 'NAME_ROLE', 'ROLE_COMPANY_TYPE', 'ANONYMOUS'
            );
        EXCEPTION WHEN duplicate_object THEN
            NULL;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE testimonial_status_enum AS ENUM (
                'NONE', 'PENDING', 'APPROVED', 'REJECTED'
            );
        EXCEPTION WHEN duplicate_object THEN
            NULL;
        END $$;
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS trial_feedback (
            id                       SERIAL PRIMARY KEY,
            email                    VARCHAR(255) NOT NULL,
            respondent_name          VARCHAR(200),
            role                     VARCHAR(200),
            company_name             VARCHAR(200),
            participant_label        VARCHAR(20),
            ease_of_use              INTEGER NOT NULL,
            setup_experience         INTEGER NOT NULL,
            data_trust               INTEGER NOT NULL,
            value_rating             INTEGER NOT NULL,
            adoption_likelihood      INTEGER NOT NULL,
            nps                      INTEGER NOT NULL,
            time_saved               VARCHAR(50),
            willingness_to_pay       VARCHAR(50),
            features_used            JSON,
            problem_solved           TEXT,
            most_valuable            TEXT,
            biggest_frustration      TEXT,
            missing_for_adoption     TEXT,
            compared_to_before       TEXT,
            other_comments           TEXT,
            research_consent         BOOLEAN NOT NULL DEFAULT FALSE,
            testimonial              TEXT,
            testimonial_consent      BOOLEAN NOT NULL DEFAULT FALSE,
            testimonial_attribution  testimonial_attribution_enum NOT NULL DEFAULT 'ANONYMOUS',
            testimonial_status       testimonial_status_enum NOT NULL DEFAULT 'NONE',
            testimonial_display_text TEXT,
            notes                    TEXT,
            created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at               TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute('CREATE INDEX IF NOT EXISTS ix_trial_feedback_id ON trial_feedback (id)')
    op.execute('CREATE INDEX IF NOT EXISTS ix_trial_feedback_email ON trial_feedback (email)')
    op.execute('CREATE INDEX IF NOT EXISTS ix_trial_feedback_testimonial_status ON trial_feedback (testimonial_status)')


def downgrade() -> None:
    op.execute('DROP INDEX IF EXISTS ix_trial_feedback_testimonial_status')
    op.execute('DROP INDEX IF EXISTS ix_trial_feedback_email')
    op.execute('DROP INDEX IF EXISTS ix_trial_feedback_id')
    op.execute('DROP TABLE IF EXISTS trial_feedback')
    op.execute('DROP TYPE IF EXISTS testimonial_status_enum')
    op.execute('DROP TYPE IF EXISTS testimonial_attribution_enum')
