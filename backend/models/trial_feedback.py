"""
Trial Feedback Model.

Post-trial questionnaire for organisations that completed a guided trial.
Captures structured ratings (usability, value, adoption intent, NPS),
open-ended answers for the trial feedback analysis, and an optional
testimonial that can only be published with explicit opt-in consent and
after super-admin approval.
"""
from datetime import datetime, timezone
import enum

from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    String,
    Text,
    DateTime,
    JSON,
    Enum as SQLEnum,
)

from backend.database import Base


class TestimonialAttribution(str, enum.Enum):
    """How the participant wants a published testimonial credited."""
    FULL = "full"                  # Name, role, company
    NAME_ROLE = "name_role"        # Name and role only (no company)
    ROLE_COMPANY_TYPE = "role_company_type"  # e.g. "Head of Finance, payments company, Nigeria"
    ANONYMOUS = "anonymous"        # "Trial participant"


class TestimonialStatus(str, enum.Enum):
    """Moderation state. Only APPROVED + consented testimonials are public."""
    NONE = "none"          # no testimonial, or no consent
    PENDING = "pending"    # consented, waiting for review
    APPROVED = "approved"
    REJECTED = "rejected"


class TrialFeedback(Base):
    __tablename__ = "trial_feedback"

    id = Column(Integer, primary_key=True, index=True)

    # Respondent (kept private; never shown publicly unless attribution allows)
    email = Column(String(255), nullable=False, index=True)
    respondent_name = Column(String(200), nullable=True)
    role = Column(String(200), nullable=True)
    company_name = Column(String(200), nullable=True)
    # Research label (P1, P2, ...) assigned by the admin, used in analysis
    participant_label = Column(String(20), nullable=True)

    # Ratings: 1-5 Likert unless noted
    ease_of_use = Column(Integer, nullable=False)
    setup_experience = Column(Integer, nullable=False)
    data_trust = Column(Integer, nullable=False)
    value_rating = Column(Integer, nullable=False)
    adoption_likelihood = Column(Integer, nullable=False)
    nps = Column(Integer, nullable=False)  # 0-10
    time_saved = Column(String(50), nullable=True)
    willingness_to_pay = Column(String(50), nullable=True)
    features_used = Column(JSON, default=list)

    # Open questions
    problem_solved = Column(Text, nullable=True)
    most_valuable = Column(Text, nullable=True)
    biggest_frustration = Column(Text, nullable=True)
    missing_for_adoption = Column(Text, nullable=True)
    compared_to_before = Column(Text, nullable=True)
    other_comments = Column(Text, nullable=True)

    # Consent
    research_consent = Column(Boolean, default=False, nullable=False)

    # Testimonial (publish only with consent + approval)
    testimonial = Column(Text, nullable=True)
    testimonial_consent = Column(Boolean, default=False, nullable=False)
    testimonial_attribution = Column(
        SQLEnum(TestimonialAttribution, name="testimonial_attribution_enum"),
        default=TestimonialAttribution.ANONYMOUS,
        nullable=False,
    )
    testimonial_status = Column(
        SQLEnum(TestimonialStatus, name="testimonial_status_enum"),
        default=TestimonialStatus.NONE,
        nullable=False,
    )
    # Admin-edited display text, e.g. trimmed for length (participant approves edits)
    testimonial_display_text = Column(Text, nullable=True)

    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
