"""
Scheduled Report Configuration Model.

Stores user-configured automated PDF report schedules.
"""
import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from backend.database import Base


class ReportFrequency(str, enum.Enum):
    """How often an automated report is sent."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class ScheduledReport(Base):
    """
    Scheduled Report model.

    Stores configuration for automated PDF reports that are emailed
    to specified recipients on a recurring schedule.
    """

    __tablename__ = "scheduled_reports"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    name = Column(String(200), nullable=False)
    frequency = Column(
        SAEnum(ReportFrequency, name="reportfrequency"),
        nullable=False,
        default=ReportFrequency.WEEKLY,
    )
    # Comma-separated list of recipient email addresses (stored as plain string)
    recipients = Column(String(2000), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # What sections to include
    include_pipelines = Column(Boolean, default=True, nullable=False)
    include_quality = Column(Boolean, default=True, nullable=False)

    # Scheduling state
    last_sent_at = Column(DateTime(timezone=True), nullable=True)
    next_send_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    organization = relationship("Organization", foreign_keys=[organization_id])
    created_by = relationship("User", foreign_keys=[created_by_id])

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def get_recipients_list(self) -> list[str]:
        """Parse recipients string into a list of email addresses."""
        if not self.recipients:
            return []
        return [e.strip() for e in self.recipients.split(",") if e.strip()]

    @property
    def period_days(self) -> int:
        """Return the look-back window in days for this frequency."""
        mapping = {
            ReportFrequency.DAILY: 1,
            ReportFrequency.WEEKLY: 7,
            ReportFrequency.MONTHLY: 30,
        }
        return mapping.get(self.frequency, 7)

    def __repr__(self) -> str:
        return (
            f"<ScheduledReport(id={self.id}, name='{self.name}', "
            f"frequency='{self.frequency}', org_id={self.organization_id})>"
        )
