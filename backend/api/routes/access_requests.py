"""
Access Request routes.

Public endpoint for the gated trial model: organizations request access
through a structured form (instead of a mailto link), then go through a
discovery call before being granted a 15-day guided trial.

Submissions are reviewed by the super admin, who invites qualified
organizations manually (self-registration is disabled).
"""
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.auth import require_super_admin
from backend.models import User
from backend.models.access_request import AccessRequest, AccessRequestStatus

router = APIRouter(prefix="/access-requests", tags=["Access Requests"])


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
