"""
Access Request Model.

Stores structured trial access requests from the public site
(gated trial model: request form -> discovery call -> 15-day guided trial).
Each request captures which digital systems the organization already uses
and what data problem they are trying to solve.
"""
from datetime import datetime, timezone

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
import enum

from backend.database import Base


class AccessRequestStatus(str, enum.Enum):
    """Lifecycle of an access request through the gated trial funnel."""
    NEW = "new"
    CONTACTED = "contacted"
    DISCOVERY_SCHEDULED = "discovery_scheduled"
    QUALIFIED = "qualified"
    TRIAL_ACTIVE = "trial_active"
    DECLINED = "declined"


class AccessRequest(Base):
    """
    A trial access request submitted from the public site.

    Replaces the old mailto link with a structured form so each request
    captures comparable data (systems in use, data problem, sector, size).
    """
    __tablename__ = "access_requests"

    id = Column(Integer, primary_key=True, index=True)

    # Contact
    company_name = Column(String(200), nullable=False)
    contact_name = Column(String(200), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    country = Column(String(100), nullable=False)

    # Qualification data
    sector = Column(String(100), nullable=False)  # e.g. digital_payments, mobile_wallet, micro_lending, other
    company_size = Column(String(50), nullable=True)  # e.g. 1-10, 11-50, 51-200
    digital_systems = Column(JSON, default=list)  # systems currently in use (min 2 to qualify)
    data_problem = Column(Text, nullable=False)  # what they are trying to solve

    # DBA research pilot: applicant read the participant information notice
    # and agreed to be contacted about the study (informed consent, stage 1;
    # full consent form is signed before the trial begins)
    research_consent = Column(Boolean, default=False, nullable=False)

    # Funnel tracking
    status = Column(
        SQLEnum(AccessRequestStatus, name="access_request_status_enum"),
        default=AccessRequestStatus.NEW,
        nullable=False,
    )
    notes = Column(Text, nullable=True)  # internal notes (discovery call outcome etc.)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
