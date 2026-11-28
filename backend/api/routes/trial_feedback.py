"""
Trial Feedback routes.

Public post-trial questionnaire (no auth, linked from the trial wrap-up
email) plus super-admin review, CSV export for analysis, and a public
testimonials feed.

Testimonials are published only when the participant ticked the explicit
publishing consent AND a super admin approved the text. Attribution
follows the participant's chosen preference; email is never exposed.
"""
import csv
import io
import logging
import threading
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from backend.auth import require_super_admin
from backend.database import get_db
from backend.models import User
from backend.models.trial_feedback import (
    TrialFeedback,
    TestimonialAttribution,
    TestimonialStatus,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/trial-feedback", tags=["Trial Feedback"])

Likert = Field(..., ge=1, le=5)
OpenText = Field(None, max_length=5000)

# Q5: tick the single most important feature
TOP_FEATURES = {
    "connecting_sources",   # Connecting my data sources
    "data_location",        # Controlling where my data is stored
    "dashboards",           # Dashboards and reporting
    "ai_insights",          # AI insights
    "local_connectors",     # Local connectors (M-Pesa, MTN, Paystack, etc.)
}

# Q7: fixed monthly price bands in naira and euro, or "other"
PRICE_BANDS = {
    "ngn_under_25k", "ngn_25k_75k", "ngn_75k_150k", "ngn_150k_300k", "ngn_over_300k",
    "eur_under_25", "eur_25_75", "eur_75_150", "eur_150_300", "eur_over_300",
    "would_not_pay", "other",
}


class TrialFeedbackCreate(BaseModel):
    email: EmailStr
    respondent_name: Optional[str] = Field(None, max_length=200)
    role: Optional[str] = Field(None, max_length=200)
    company_name: Optional[str] = Field(None, max_length=200)

    # Section A: the problem and the fit
    problem_relevance: int = Likert
    hardest_systems: Optional[str] = OpenText
    biggest_concern: Optional[str] = OpenText
    # Section B: value and priorities
    continue_likelihood: int = Likert
    top_feature: Optional[str] = Field(None, max_length=100)
    top_feature_reason: Optional[str] = OpenText
    local_storage_importance: int = Likert
    # Section C: pricing and recommendation
    price_band: Optional[str] = Field(None, max_length=50)
    price_other: Optional[str] = Field(None, max_length=200)
    nps: int = Field(..., ge=0, le=10)
    other_comments: Optional[str] = OpenText

    research_consent: bool = False
    quote_consent: bool = False

    testimonial: Optional[str] = Field(None, max_length=600)
    testimonial_consent: bool = False
    testimonial_attribution: TestimonialAttribution = TestimonialAttribution.ANONYMOUS


class TrialFeedbackResponse(BaseModel):
    id: int
    email: str
    respondent_name: Optional[str]
    role: Optional[str]
    company_name: Optional[str]
    participant_label: Optional[str]
    sector_label: Optional[str] = None
    size_label: Optional[str] = None
    problem_relevance: Optional[int] = None
    hardest_systems: Optional[str] = None
    biggest_concern: Optional[str] = None
    continue_likelihood: Optional[int] = None
    top_feature: Optional[str] = None
    top_feature_reason: Optional[str] = None
    local_storage_importance: Optional[int] = None
    price_band: Optional[str] = None
    price_other: Optional[str] = None
    nps: int
    other_comments: Optional[str]
    # Earlier draft questions (responses collected before 28 Nov 2026)
    ease_of_use: Optional[int] = None
    setup_experience: Optional[int] = None
    data_trust: Optional[int] = None
    value_rating: Optional[int] = None
    adoption_likelihood: Optional[int] = None
    time_saved: Optional[str] = None
    willingness_to_pay: Optional[str] = None
    features_used: Optional[List[str]] = None
    problem_solved: Optional[str] = None
    most_valuable: Optional[str] = None
    biggest_frustration: Optional[str] = None
    missing_for_adoption: Optional[str] = None
    compared_to_before: Optional[str] = None
    research_consent: bool
    quote_consent: bool = False
    testimonial: Optional[str]
    testimonial_consent: bool
    testimonial_attribution: TestimonialAttribution
    testimonial_status: TestimonialStatus
    testimonial_display_text: Optional[str]
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class TrialFeedbackUpdate(BaseModel):
    participant_label: Optional[str] = Field(None, max_length=20)
    sector_label: Optional[str] = Field(None, max_length=100)
    size_label: Optional[str] = Field(None, max_length=50)
    testimonial_status: Optional[TestimonialStatus] = None
    testimonial_display_text: Optional[str] = Field(None, max_length=600)
    notes: Optional[str] = Field(None, max_length=10000)


class PublicTestimonial(BaseModel):
    id: int
    quote: str
    attribution: str


def _clean(v: Optional[str]) -> Optional[str]:
    v = (v or "").strip()
    return v or None


def _attribution_error(p: "TrialFeedbackCreate") -> Optional[str]:
    """The chosen credit line must be buildable from the details given."""
    if not (p.testimonial_consent and (p.testimonial or "").strip()):
        return None
    a = p.testimonial_attribution
    has = lambda v: bool((v or "").strip())  # noqa: E731
    if a in (TestimonialAttribution.FULL, TestimonialAttribution.NAME_ROLE) and not (
        has(p.respondent_name) and has(p.role)
    ):
        return "Name and role are needed for the chosen attribution."
    if a == TestimonialAttribution.FULL and not has(p.company_name):
        return "Company name is needed for full attribution."
    if a == TestimonialAttribution.ROLE_COMPANY_TYPE and not has(p.role):
        return "Role is needed for the chosen attribution."
    return None


def attribution_line(fb: TrialFeedback) -> str:
    """Public credit line, built strictly from the participant's preference."""
    a = fb.testimonial_attribution
    if a == TestimonialAttribution.FULL:
        return f"{fb.respondent_name}, {fb.role}, {fb.company_name}"
    if a == TestimonialAttribution.NAME_ROLE:
        return f"{fb.respondent_name}, {fb.role}"
    if a == TestimonialAttribution.ROLE_COMPANY_TYPE:
        return f"{fb.role}, fintech company"
    return "Trial participant, fintech company"


def _notify(admin_emails: List[str], fb_id: int, nps: int, has_testimonial: bool) -> None:
    from backend.notifications import email_notifier

    try:
        email_notifier.send(
            to_emails=admin_emails,
            subject=f"New trial feedback received (NPS {nps})",
            body=(
                f"<p>A trial participant submitted post-trial feedback (id {fb_id}, NPS {nps}).</p>"
                + ("<p>It includes a testimonial with publishing consent, waiting for review.</p>"
                   if has_testimonial else "")
                + "<p>Review it in the admin panel under Trial Feedback.</p>"
            ),
            html=True,
        )
    except Exception:
        logger.exception("Failed to send trial-feedback notification email")


@router.post("", status_code=status.HTTP_201_CREATED)
def submit_trial_feedback(payload: TrialFeedbackCreate, db: Session = Depends(get_db)):
    """Submit post-trial feedback (public, no auth)."""
    if payload.top_feature and payload.top_feature not in TOP_FEATURES:
        raise HTTPException(status_code=422, detail="Unknown feature option.")
    if payload.price_band and payload.price_band not in PRICE_BANDS:
        raise HTTPException(status_code=422, detail="Unknown price option.")
    err = _attribution_error(payload)
    if err:
        raise HTTPException(status_code=422, detail=err)
    testimonial = _clean(payload.testimonial)
    publishable = bool(testimonial and payload.testimonial_consent)

    fb = TrialFeedback(
        email=payload.email.lower(),
        respondent_name=_clean(payload.respondent_name),
        role=_clean(payload.role),
        company_name=_clean(payload.company_name),
        problem_relevance=payload.problem_relevance,
        hardest_systems=_clean(payload.hardest_systems),
        biggest_concern=_clean(payload.biggest_concern),
        continue_likelihood=payload.continue_likelihood,
        top_feature=payload.top_feature,
        top_feature_reason=_clean(payload.top_feature_reason),
        local_storage_importance=payload.local_storage_importance,
        price_band=payload.price_band,
        price_other=_clean(payload.price_other) if payload.price_band == "other" else None,
        nps=payload.nps,
        other_comments=_clean(payload.other_comments),
        research_consent=payload.research_consent,
        quote_consent=payload.quote_consent,
        testimonial=testimonial,
        testimonial_consent=publishable,
        testimonial_attribution=payload.testimonial_attribution,
        testimonial_status=TestimonialStatus.PENDING if publishable else TestimonialStatus.NONE,
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)

    from backend.config import settings

    if settings.ACCESS_REQUEST_NOTIFY_EMAILS:
        admin_emails = [e.strip() for e in settings.ACCESS_REQUEST_NOTIFY_EMAILS.split(",") if e.strip()]
    else:
        admin_emails = [
            u.email
            for u in db.query(User).filter(User.is_superuser.is_(True), User.is_active.is_(True)).all()
        ]
    if admin_emails:
        threading.Thread(
            target=_notify, args=(admin_emails, fb.id, fb.nps, publishable), daemon=True
        ).start()

    return {"message": "Thank you. Your feedback has been received."}


@router.get("/testimonials", response_model=List[PublicTestimonial])
def list_public_testimonials(db: Session = Depends(get_db)):
    """Approved, consented testimonials for the public site (no auth)."""
    rows = (
        db.query(TrialFeedback)
        .filter(
            TrialFeedback.testimonial_consent.is_(True),
            TrialFeedback.testimonial_status == TestimonialStatus.APPROVED,
        )
        .order_by(TrialFeedback.created_at.desc())
        .all()
    )
    return [
        PublicTestimonial(
            id=r.id,
            quote=r.testimonial_display_text or r.testimonial,
            attribution=attribution_line(r),
        )
        for r in rows
        if (r.testimonial_display_text or r.testimonial)
    ]


@router.get("", response_model=List[TrialFeedbackResponse])
def list_trial_feedback(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    """List all feedback (super admin only)."""
    return db.query(TrialFeedback).order_by(TrialFeedback.created_at.desc()).all()


EXPORT_COLUMNS = [
    "id", "participant_label", "sector_label", "size_label", "created_at",
    "problem_relevance", "hardest_systems", "biggest_concern",
    "continue_likelihood", "top_feature", "top_feature_reason",
    "local_storage_importance", "price_band", "price_other", "nps",
    "other_comments", "research_consent", "quote_consent",
    "testimonial_consent", "testimonial_status",
]


@router.get("/export.csv")
def export_trial_feedback_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    """Anonymised CSV for analysis (super admin only).

    Leaves out email, name, role and company so the file can go straight into
    the research analysis; rows are identified by participant label only.
    """
    rows = db.query(TrialFeedback).order_by(TrialFeedback.created_at.asc()).all()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(EXPORT_COLUMNS)
    for r in rows:
        out = []
        for col in EXPORT_COLUMNS:
            v = getattr(r, col)
            if hasattr(v, "value"):
                v = v.value
            elif isinstance(v, datetime):
                v = v.isoformat()
            out.append("" if v is None else v)
        writer.writerow(out)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="trial-feedback-anonymised.csv"'},
    )


@router.patch("/{feedback_id}", response_model=TrialFeedbackResponse)
def update_trial_feedback(
    feedback_id: int,
    payload: TrialFeedbackUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    """Label a response or moderate its testimonial (super admin only)."""
    fb = db.query(TrialFeedback).filter(TrialFeedback.id == feedback_id).first()
    if not fb:
        raise HTTPException(status_code=404, detail="Feedback not found")

    if payload.testimonial_status is not None:
        if payload.testimonial_status == TestimonialStatus.APPROVED and not (
            fb.testimonial_consent and fb.testimonial
        ):
            raise HTTPException(
                status_code=400,
                detail="Cannot publish: the participant did not consent to publishing a testimonial.",
            )
        fb.testimonial_status = payload.testimonial_status
    if payload.participant_label is not None:
        fb.participant_label = _clean(payload.participant_label)
    if payload.sector_label is not None:
        fb.sector_label = _clean(payload.sector_label)
    if payload.size_label is not None:
        fb.size_label = _clean(payload.size_label)
    if payload.testimonial_display_text is not None:
        fb.testimonial_display_text = _clean(payload.testimonial_display_text)
    if payload.notes is not None:
        fb.notes = payload.notes
    fb.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(fb)
    return fb


@router.delete("/{feedback_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trial_feedback(
    feedback_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    """Delete a response, e.g. a test submission or a consent withdrawal (super admin only)."""
    fb = db.query(TrialFeedback).filter(TrialFeedback.id == feedback_id).first()
    if not fb:
        raise HTTPException(status_code=404, detail="Feedback not found")
    db.delete(fb)
    db.commit()
