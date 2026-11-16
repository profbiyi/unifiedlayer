"""
Access Request routes.

Public endpoint for the gated trial model: organizations request access
through a structured form (instead of a mailto link), then go through a
discovery call before being granted a 15-day guided trial.

Submissions are reviewed by the super admin, who invites qualified
organizations manually (self-registration is disabled).
"""
import html as html_lib
import logging
import re
import secrets
import threading
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db
from backend.auth import require_super_admin, get_password_hash
from backend.models import User, Organization
from backend.models.access_request import AccessRequest, AccessRequestStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/access-requests", tags=["Access Requests"])


def _build_notification_html(request: "AccessRequestCreate") -> str:
    """Branded, email-client-safe HTML for the new-lead alert.

    All user-supplied values are HTML-escaped — this content lands in the
    team inbox and must not be able to inject markup.
    """
    e = html_lib.escape
    systems = ", ".join(e(s) for s in request.digital_systems) or "none listed"
    admin_url = f"{settings.FRONTEND_URL.rstrip('/')}/admin/access-requests"

    def row(label: str, value: str) -> str:
        return (
            '<tr>'
            f'<td style="padding:8px 16px 8px 0;color:#64748b;font-size:14px;'
            f'white-space:nowrap;vertical-align:top;">{label}</td>'
            f'<td style="padding:8px 0;color:#0f172a;font-size:14px;font-weight:500;">{value}</td>'
            '</tr>'
        )

    return f"""\
<!doctype html>
<html>
  <body style="margin:0;padding:0;background-color:#f1f5f9;">
    <div style="max-width:600px;margin:0 auto;padding:24px 16px;
                font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
      <div style="background:#2563eb;border-radius:12px 12px 0 0;padding:20px 28px;">
        <p style="margin:0;color:#ffffff;font-size:18px;font-weight:700;">UnifiedLayer</p>
        <p style="margin:4px 0 0;color:#bfdbfe;font-size:13px;">New trial access request</p>
      </div>
      <div style="background:#ffffff;border-radius:0 0 12px 12px;padding:28px;
                  border:1px solid #e2e8f0;border-top:none;">
        <h1 style="margin:0 0 4px;font-size:20px;color:#0f172a;">{e(request.company_name)}</h1>
        <p style="margin:0 0 20px;color:#64748b;font-size:14px;">
          just requested a guided trial from {e(request.country)}.
        </p>

        <table cellpadding="0" cellspacing="0" style="width:100%;border-collapse:collapse;">
          {row("Contact", f"{e(request.contact_name)} &lt;{e(request.email)}&gt;")}
          {row("Sector", e(request.sector))}
          {row("Company size", e(request.company_size or "not given"))}
          {row("Systems in use", systems)}
          {row("Research pilot", "&#9989; Consented to be contacted" if request.research_consent else "Not indicated")}
        </table>

        <div style="margin:20px 0;padding:16px;background:#f8fafc;border-left:3px solid #2563eb;
                    border-radius:0 8px 8px 0;">
          <p style="margin:0 0 4px;color:#64748b;font-size:12px;text-transform:uppercase;
                    letter-spacing:0.05em;">The problem they want solved</p>
          <p style="margin:0;color:#0f172a;font-size:14px;line-height:1.6;">{e(request.data_problem)}</p>
        </div>

        <a href="{admin_url}"
           style="display:inline-block;background:#2563eb;color:#ffffff;text-decoration:none;
                  padding:12px 24px;border-radius:8px;font-size:14px;font-weight:600;">
          Review in Admin Panel
        </a>

        <p style="margin:24px 0 0;color:#94a3b8;font-size:12px;line-height:1.5;">
          Next step: schedule the 15&ndash;20 minute discovery call, then move the
          request through the funnel.
        </p>
      </div>
      <p style="margin:16px 0 0;text-align:center;color:#94a3b8;font-size:12px;">
        UnifiedLayer &middot; sent to the access-request notification list
      </p>
    </div>
  </body>
</html>"""


def _notify_super_admins(admin_emails: List[str], request: "AccessRequestCreate") -> None:
    """Email super admins about a new access request (best-effort, in background)."""
    from backend.notifications import email_notifier

    try:
        email_notifier.send(
            to_emails=admin_emails,
            subject=f"New access request: {request.company_name} ({request.country})",
            body=_build_notification_html(request),
            html=True,
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
    # Stage-1 research consent: read the participant information notice and
    # agreed to be contacted about the DBA Phase 2 pilot
    research_consent: bool = False


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
    research_consent: bool
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
        research_consent=payload.research_consent,
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


@router.delete("/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_access_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    """Permanently delete an access request (super admin only).

    Intended for test submissions and withdrawn applicants. Real research
    leads should normally be kept and moved to DECLINED instead, so the
    funnel history stays complete.
    """
    request = db.query(AccessRequest).filter(AccessRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Access request not found")

    db.delete(request)
    db.commit()


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


# ---------------------------------------------------------------------------
# One-click onboarding: turn a qualified access request into a real account
# ---------------------------------------------------------------------------

class OnboardRequest(BaseModel):
    subscription_plan: str = Field(
        default="professional",
        description="starter | professional | enterprise (trial tier for the pilot)",
    )


class OnboardResult(BaseModel):
    organization_id: int
    organization_slug: str
    admin_email: str
    admin_username: str
    temporary_password: str
    message: str


def _slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    return s[:90] or "org"


def _unique_org_slug(db: Session, base: str) -> str:
    slug, i = base, 2
    while db.query(Organization).filter(Organization.slug == slug).first():
        slug = f"{base}-{i}"[:100]
        i += 1
    return slug


def _unique_username(db: Session, email: str, contact: Optional[str]) -> str:
    base = re.sub(r"[^a-z0-9_]+", "", (email.split("@")[0] or (contact or "")).lower())[:40] or "user"
    uname, i = base, 2
    while db.query(User).filter(User.username == uname).first():
        uname = f"{base}{i}"
        i += 1
    return uname


@router.post("/{request_id}/onboard", response_model=OnboardResult)
def onboard_access_request(
    request_id: int,
    payload: OnboardRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    """
    Provision a real account (organization + admin user) from a qualified access
    request — the one-click alternative to re-keying everything into the admin
    onboarding form.

    **Super Admin Only.** Creates the org, its subscription (currency from the
    request's country), an ORG_ADMIN user with a generated temporary password,
    emails the welcome/login details, and flips the request to ``trial_active``.
    The temporary password is returned so you can relay it if the email bounces.
    """
    if payload.subscription_plan not in ("starter", "professional", "enterprise"):
        raise HTTPException(status_code=400, detail="Invalid subscription plan")

    request = db.query(AccessRequest).filter(AccessRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Access request not found")

    # Already has an account? Don't create a duplicate.
    if db.query(User).filter(User.email == request.email).first():
        raise HTTPException(
            status_code=409,
            detail=f"A user with email {request.email} already exists — this request looks already onboarded.",
        )

    from backend.api.routes.admin import _create_org_subscription
    from backend.models.rbac import Role, UserRole

    org_admin_role = db.query(Role).filter(Role.slug == "org_admin").first()
    if not org_admin_role:
        raise HTTPException(status_code=500, detail="ORG_ADMIN role not found")

    slug = _unique_org_slug(db, _slugify(request.company_name))
    temp_password = secrets.token_urlsafe(12)

    organization = Organization(
        name=request.company_name,
        slug=slug,
        description=f"Research/testing pilot. Sector: {request.sector}.",
        country=request.country,
        subscription_plan=payload.subscription_plan,
        billing_email=request.email,
        is_active=True,
    )
    db.add(organization)
    db.flush()

    _create_org_subscription(db, organization, payload.subscription_plan, request.country)

    username = _unique_username(db, request.email, request.contact_name)
    admin_user = User(
        organization_id=organization.id,
        email=request.email,
        username=username,
        full_name=request.contact_name,
        hashed_password=get_password_hash(temp_password),
        is_active=True,
        is_superuser=False,
        email_verified=True,
    )
    db.add(admin_user)
    db.flush()

    db.add(UserRole(
        user_id=admin_user.id,
        role_id=org_admin_role.id,
        organization_id=organization.id,
        assigned_by_id=current_user.id,
    ))

    # Advance the funnel + record what happened.
    request.status = AccessRequestStatus.TRIAL_ACTIVE
    note = (
        f"Onboarded {datetime.now(timezone.utc):%Y-%m-%d} as org '{slug}' "
        f"(admin {request.email}, plan {payload.subscription_plan})."
    )
    request.notes = f"{request.notes}\n{note}" if request.notes else note
    request.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(organization)
    db.refresh(admin_user)

    logger.info("Onboarded access request %s -> org %s (%s)", request_id, slug, request.email)

    # Welcome email in the background (don't block the response).
    def _send_welcome():
        try:
            from backend.notifications import email_notifier
            email_notifier.send_welcome_email(
                to_email=admin_user.email,
                user_name=admin_user.full_name or admin_user.username,
                organization_name=organization.name,
                login_url=f"{settings.FRONTEND_URL}/login",
                temporary_password=temp_password,
            )
        except Exception as exc:  # noqa: BLE001 — email is best-effort
            logger.warning("Welcome email to %s failed: %s", admin_user.email, exc)

    threading.Thread(target=_send_welcome).start()

    return OnboardResult(
        organization_id=organization.id,
        organization_slug=slug,
        admin_email=admin_user.email,
        admin_username=username,
        temporary_password=temp_password,
        message=f"Onboarded '{organization.name}'. Welcome email sent to {admin_user.email}.",
    )
