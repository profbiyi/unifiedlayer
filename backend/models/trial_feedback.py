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

    # Researcher-assigned labels (never shown to the participant)
    sector_label = Column(String(100), nullable=True)
    size_label = Column(String(50), nullable=True)

    # --- Final questionnaire (Nov 2026) ---
    # Section A: the problem and the fit
    problem_relevance = Column(Integer, nullable=True)        # Q1, 1-5
    hardest_systems = Column(Text, nullable=True)             # Q2
    biggest_concern = Column(Text, nullable=True)             # Q3
    # Section B: value and priorities
    continue_likelihood = Column(Integer, nullable=True)      # Q4, 1-5
    top_feature = Column(String(100), nullable=True)          # Q5, single choice
    top_feature_reason = Column(Text, nullable=True)          # Q5, optional why
    local_storage_importance = Column(Integer, nullable=True) # Q6, 1-5
    # Section C: pricing and recommendation
    price_band = Column(String(50), nullable=True)            # Q7, fixed band or "other"
    price_other = Column(String(200), nullable=True)          # Q7, free text when "other"
    nps = Column(Integer, nullable=False)                     # Q8, 0-10
    other_comments = Column(Text, nullable=True)              # closing open question

    # --- Earlier draft questions (kept nullable so early responses survive) ---
    ease_of_use = Column(Integer, nullable=True)
    setup_experience = Column(Integer, nullable=True)
    data_trust = Column(Integer, nullable=True)
    value_rating = Column(Integer, nullable=True)
    adoption_likelihood = Column(Integer, nullable=True)
    time_saved = Column(String(50), nullable=True)
    willingness_to_pay = Column(String(50), nullable=True)
    features_used = Column(JSON, default=list)
    problem_solved = Column(Text, nullable=True)
    most_valuable = Column(Text, nullable=True)
    biggest_frustration = Column(Text, nullable=True)
    missing_for_adoption = Column(Text, nullable=True)
    compared_to_before = Column(Text, nullable=True)

    # Consent
    research_consent = Column(Boolean, default=False, nullable=False)
    # Agreed that anonymised quotes from their open answers may appear in the research
    quote_consent = Column(Boolean, default=False, nullable=False)

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
