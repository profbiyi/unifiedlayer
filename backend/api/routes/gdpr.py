"""
GDPR compliance API routes.

Provides data export, account deletion, and data processing information
endpoints to comply with GDPR, POPIA, and NDPR regulations.
"""
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.auth import get_current_user, verify_password
from backend.models.pipeline import (
    User,
    Organization,
    DataSource,
    Destination,
    Pipeline,
    PipelineRun,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/gdpr", tags=["GDPR"])


class DeleteAccountRequest(BaseModel):
    password: str
    confirmation: str


def _serialize_datetime(obj):
    """JSON serializer for datetime objects."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


@router.get("/export-my-data")
async def export_my_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Export all data associated with the authenticated user.

    Returns a downloadable JSON file containing the user's profile,
    organization, sources, destinations, pipelines, and pipeline runs.
    """
    org = db.query(Organization).filter(
        Organization.id == current_user.organization_id
    ).first()

    sources = db.query(DataSource).filter(
        DataSource.organization_id == current_user.organization_id
    ).all()

    destinations = db.query(Destination).filter(
        Destination.organization_id == current_user.organization_id
    ).all()

    pipelines = db.query(Pipeline).filter(
        Pipeline.organization_id == current_user.organization_id
    ).all()

    pipeline_ids = [p.id for p in pipelines]
    runs = db.query(PipelineRun).filter(
        PipelineRun.pipeline_id.in_(pipeline_ids)
    ).all() if pipeline_ids else []

    export_data = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "user": {
            "id": str(current_user.public_id),
            "email": current_user.email,
            "username": current_user.username,
            "full_name": current_user.full_name,
            "is_active": current_user.is_active,
            "email_verified": current_user.email_verified,
            "last_login": current_user.last_login,
            "created_at": current_user.created_at,
            "updated_at": current_user.updated_at,
        },
        "organization": {
            "id": str(org.public_id) if org else None,
            "name": org.name if org else None,
            "slug": org.slug if org else None,
            "subscription_plan": org.subscription_plan if org else None,
            "created_at": org.created_at if org else None,
        },
        "data_sources": [
            {
                "id": str(s.public_id),
                "name": s.name,
                "description": s.description,
                "source_type": s.source_type.value if s.source_type else None,
                "is_active": s.is_active,
                "created_at": s.created_at,
            }
            for s in sources
        ],
        "destinations": [
            {
                "id": str(d.public_id),
                "name": d.name,
                "description": d.description,
                "destination_type": d.destination_type.value if d.destination_type else None,
                "is_active": d.is_active,
                "created_at": d.created_at,
            }
            for d in destinations
        ],
        "pipelines": [
            {
                "id": str(p.public_id),
                "name": p.name,
                "description": p.description,
                "schedule": p.schedule,
                "is_active": p.is_active,
                "created_at": p.created_at,
            }
            for p in pipelines
        ],
        "pipeline_runs": [
            {
                "id": str(r.public_id),
                "pipeline_id": str(
                    next((p.public_id for p in pipelines if p.id == r.pipeline_id), r.pipeline_id)
                ),
                "status": r.status.value if r.status else None,
                "started_at": r.started_at,
                "completed_at": r.completed_at,
                "rows_read": r.rows_read,
                "rows_written": r.rows_written,
                "created_at": r.created_at,
            }
            for r in runs
        ],
    }

    content = json.dumps(export_data, indent=2, default=_serialize_datetime)

    return StreamingResponse(
        iter([content]),
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=data_export_{current_user.id}.json"
        },
    )


@router.delete("/delete-my-account")
async def delete_my_account(
    payload: DeleteAccountRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Permanently delete (anonymise) the authenticated user's account.

    Requires the user's current password and the confirmation string "DELETE".
    If the user is the only admin in their organisation, the request is rejected
    to prevent orphaned organisations.
    """
    # Verify confirmation string
    if payload.confirmation != "DELETE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='You must type "DELETE" to confirm account deletion.',
        )

    # Verify password
    if not verify_password(payload.password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password.",
        )

    # Check if user is the only admin in their organisation
    if current_user.is_org_admin():
        from backend.models.rbac import UserRole, Role

        admin_count = (
            db.query(User)
            .join(UserRole, UserRole.user_id == User.id)
            .join(Role, Role.id == UserRole.role_id)
            .filter(
                User.organization_id == current_user.organization_id,
                User.is_active,
                Role.slug == "org_admin",
                User.id != current_user.id,
            )
            .count()
        )

        if admin_count == 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You are the only admin in your organisation. "
                       "Please transfer admin rights to another user before deleting your account.",
            )

    # Anonymise the user
    current_user.is_active = False
    current_user.email = f"deleted_{current_user.id}@deleted.local"
    current_user.username = f"deleted_user_{current_user.id}"
    current_user.full_name = None
    current_user.hashed_password = "DELETED"
    current_user.email_verification_token = None
    current_user.password_reset_token = None
    current_user.password_reset_expires = None
    current_user.invitation_token = None
    current_user.updated_at = datetime.now(timezone.utc)

    db.commit()

    logger.info("User %s account anonymised (GDPR deletion)", current_user.id)

    return {"message": "Your account has been permanently deleted and your data anonymised."}


@router.get("/data-processing-info")
async def data_processing_info():
    """
    Public endpoint describing what personal data is collected,
    the purposes of processing, data retention periods, and third parties.
    """
    return {
        "data_collected": {
            "account_data": [
                "Email address",
                "Username",
                "Full name (optional)",
                "Hashed password (bcrypt)",
                "Organisation membership",
            ],
            "usage_data": [
                "Pipeline configurations and run history",
                "Data source and destination metadata",
                "Login timestamps and IP addresses (via server logs)",
                "API request logs",
            ],
            "billing_data": [
                "Billing email address",
                "Subscription plan and status",
                "Payment information is processed by Stripe and never stored on our servers",
            ],
        },
        "purposes": [
            "Providing and operating the data integration platform",
            "User authentication and account management",
            "Pipeline orchestration, scheduling, and monitoring",
            "Billing and subscription management",
            "Platform security, abuse prevention, and audit logging",
            "Service improvement and analytics (aggregated, non-personal)",
        ],
        "retention": {
            "account_data": "Retained while your account is active. Anonymised upon account deletion.",
            "pipeline_run_logs": "Retained for 90 days after pipeline execution, then automatically purged.",
            "audit_logs": "Retained for 12 months for security and compliance purposes.",
            "billing_records": "Retained for 7 years in accordance with financial regulations.",
            "server_logs": "Retained for 30 days, then automatically deleted.",
        },
        "third_parties": [
            {
                "name": "Stripe",
                "purpose": "Payment processing",
                "data_shared": "Billing email, subscription events",
            },
            {
                "name": "Infrastructure provider (cloud hosting)",
                "purpose": "Platform hosting and data storage",
                "data_shared": "All platform data is stored on encrypted infrastructure",
            },
        ],
        "your_rights": {
            "description": "Under GDPR, POPIA, and NDPR you have the right to:",
            "rights": [
                "Access your personal data (GET /gdpr/export-my-data)",
                "Rectify inaccurate data (via account settings)",
                "Erase your data / right to be forgotten (DELETE /gdpr/delete-my-account)",
                "Data portability (GET /gdpr/export-my-data provides machine-readable JSON)",
                "Object to processing",
                "Withdraw consent at any time",
            ],
            "contact": "privacy@unifiedlayer.io",
        },
        "legal_basis": "Contractual necessity (Article 6(1)(b) GDPR) and legitimate interest (Article 6(1)(f) GDPR).",
    }
