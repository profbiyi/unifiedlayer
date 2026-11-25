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


class TrialFeedbackCreate(BaseModel):
    email: EmailStr
    respondent_name: Optional[str] = Field(None, max_length=200)
    role: Optional[str] = Field(None, max_length=200)
    company_name: Optional[str] = Field(None, max_length=200)

    ease_of_use: int = Likert
    setup_experience: int = Likert
    data_trust: int = Likert
    value_rating: int = Likert
    adoption_likelihood: int = Likert
    nps: int = Field(..., ge=0, le=10)
    time_saved: Optional[str] = Field(None, max_length=50)
    willingness_to_pay: Optional[str] = Field(None, max_length=50)
    features_used: List[str] = Field(default_factory=list, max_length=30)

    problem_solved: Optional[str] = OpenText
    most_valuable: Optional[str] = OpenText
    biggest_frustration: Optional[str] = OpenText
    missing_for_adoption: Optional[str] = OpenText
    compared_to_before: Optional[str] = OpenText
    other_comments: Optional[str] = OpenText

    research_consent: bool = False

    testimonial: Optional[str] = Field(None, max_length=600)
    testimonial_consent: bool = False
    testimonial_attribution: TestimonialAttribution = TestimonialAttribution.ANONYMOUS


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


class TrialFeedbackResponse(BaseModel):
    id: int
    email: str
    respondent_name: Optional[str]
    role: Optional[str]
    company_name: Optional[str]
    participant_label: Optional[str]
    ease_of_use: int
    setup_experience: int
    data_trust: int
    value_rating: int
    adoption_likelihood: int
    nps: int
    time_saved: Optional[str]
    willingness_to_pay: Optional[str]
    features_used: List[str]
    problem_solved: Optional[str]
    most_valuable: Optional[str]
    biggest_frustration: Optional[str]
    missing_for_adoption: Optional[str]
    compared_to_before: Optional[str]
    other_comments: Optional[str]
    research_consent: bool
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
        ease_of_use=payload.ease_of_use,
        setup_experience=payload.setup_experience,
        data_trust=payload.data_trust,
        value_rating=payload.value_rating,
        adoption_likelihood=payload.adoption_likelihood,
        nps=payload.nps,
        time_saved=payload.time_saved,
        willingness_to_pay=payload.willingness_to_pay,
        features_used=payload.features_used,
        problem_solved=_clean(payload.problem_solved),
        most_valuable=_clean(payload.most_valuable),
        biggest_frustration=_clean(payload.biggest_frustration),
        missing_for_adoption=_clean(payload.missing_for_adoption),
        compared_to_before=_clean(payload.compared_to_before),
        other_comments=_clean(payload.other_comments),
        research_consent=payload.research_consent,
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
    "id", "participant_label", "created_at", "ease_of_use", "setup_experience",
    "data_trust", "value_rating", "adoption_likelihood", "nps", "time_saved",
    "willingness_to_pay", "features_used", "problem_solved", "most_valuable",
    "biggest_frustration", "missing_for_adoption", "compared_to_before",
    "other_comments", "research_consent", "testimonial_consent", "testimonial_status",
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
            if col == "features_used":
                v = "; ".join(v or [])
            elif hasattr(v, "value"):
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
