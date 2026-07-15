"""
Access Request routes.

Public endpoint for the gated trial model: organizations request access
through a structured form (instead of a mailto link), then go through a
discovery call before being granted a 15-day guided trial.

Submissions are reviewed by the super admin, who invites qualified
organizations manually (self-registration is disabled).
"""
import logging
import threading
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.auth import require_super_admin
from backend.models import User
from backend.models.access_request import AccessRequest, AccessRequestStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/access-requests", tags=["Access Requests"])


def _notify_super_admins(admin_emails: List[str], request: "AccessRequestCreate") -> None:
    """Email super admins about a new access request (best-effort, in background)."""
    from backend.notifications import email_notifier

    systems = ", ".join(request.digital_systems) or "none listed"
    body = (
        "A new trial access request just came in.\n\n"
        f"Company:  {request.company_name}\n"
        f"Contact:  {request.contact_name} <{request.email}>\n"
        f"Country:  {request.country}\n"
        f"Sector:   {request.sector}\n"
        f"Size:     {request.company_size or 'not given'}\n"
        f"Systems:  {systems}\n\n"
        f"Data problem:\n{request.data_problem}\n\n"
        "Review it in the admin panel under Access Requests, then schedule "
        "the discovery call."
    )
    try:
        email_notifier.send(
            to_emails=admin_emails,
            subject=f"New access request: {request.company_name} ({request.country})",
            body=body,
        )
    except Exception:
        logger.exception("Failed to send access-request notification email")


class AccessRequestCreate(BaseModel):
    company_name: str = Field(..., min_length=2, max_length=200)
    contact_name: str = Field(..., min_length=2, max_length=200)
    email: EmailStr
    country: str = Field(..., min_length=2, max_length=100)
    sector: str = Field(..., min_length=2, max_length=100)
    company_size: Optional[str] = Field(None, max_length=50)
    digital_systems: List[str] = Field(default_factory=list, max_length=30)
    data_problem: str = Field(..., min_length=10, max_length=5000)


class AccessRequestResponse(BaseModel):
    id: int
    company_name: str
    contact_name: str
    email: str
    country: str
    sector: str
    company_size: Optional[str]
    digital_systems: List[str]
    data_problem: str
    status: AccessRequestStatus
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class AccessRequestUpdate(BaseModel):
    status: Optional[AccessRequestStatus] = None
    notes: Optional[str] = Field(None, max_length=10000)


@router.post("", status_code=status.HTTP_201_CREATED)
def submit_access_request(
    payload: AccessRequestCreate,
    db: Session = Depends(get_db),
):
    """Submit a trial access request (public, no auth)."""
    # Soft duplicate guard: one pending request per email
    existing = (
        db.query(AccessRequest)
        .filter(
            AccessRequest.email == payload.email.lower(),
            AccessRequest.status == AccessRequestStatus.NEW,
        )
        .first()
    )
    if existing:
        # Don't create a duplicate; respond as if accepted so the form UX stays simple
        return {"message": "Request received. We will be in touch to schedule a discovery call."}

    request = AccessRequest(
        company_name=payload.company_name.strip(),
        contact_name=payload.contact_name.strip(),
        email=payload.email.lower(),
        country=payload.country.strip(),
        sector=payload.sector.strip(),
        company_size=payload.company_size,
        digital_systems=payload.digital_systems,
        data_problem=payload.data_problem.strip(),
        status=AccessRequestStatus.NEW,
    )
    db.add(request)
    db.commit()

    # Alert the team so no lead sits unseen (best-effort, non-blocking).
    # ACCESS_REQUEST_NOTIFY_EMAILS overrides; falls back to super admin accounts.
    from backend.config import settings

    if settings.ACCESS_REQUEST_NOTIFY_EMAILS:
        admin_emails = [
            e.strip()
            for e in settings.ACCESS_REQUEST_NOTIFY_EMAILS.split(",")
            if e.strip()
        ]
    else:
        admin_emails = [
            u.email
            for u in db.query(User).filter(User.is_superuser.is_(True), User.is_active.is_(True)).all()
        ]
    if admin_emails:
        threading.Thread(
            target=_notify_super_admins, args=(admin_emails, payload), daemon=True
        ).start()

    return {"message": "Request received. We will be in touch to schedule a discovery call."}


@router.get("", response_model=List[AccessRequestResponse])
def list_access_requests(
    status_filter: Optional[AccessRequestStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    """List access requests (super admin only)."""
    query = db.query(AccessRequest)
    if status_filter is not None:
        query = query.filter(AccessRequest.status == status_filter)
    return query.order_by(AccessRequest.created_at.desc()).all()


@router.patch("/{request_id}", response_model=AccessRequestResponse)
def update_access_request(
    request_id: int,
    payload: AccessRequestUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    """Update an access request's status/notes (super admin only)."""
    request = db.query(AccessRequest).filter(AccessRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Access request not found")

    if payload.status is not None:
        request.status = payload.status
    if payload.notes is not None:
        request.notes = payload.notes
    request.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(request)
    return request
