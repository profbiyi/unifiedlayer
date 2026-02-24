"""
Onboarding Models.

Tracks user onboarding progress and preferences.
"""
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
    Enum as SQLEnum,
)
from sqlalchemy.orm import relationship
import enum

from backend.database import Base


class UserRole(str, enum.Enum):
    """User's business role for personalized onboarding."""
    FOUNDER = "founder"
    FINANCE = "finance"
    OPERATIONS = "operations"
    SALES = "sales"
    DEVELOPER = "developer"
    OTHER = "other"


class OnboardingStatus(str, enum.Enum):
    """Overall onboarding status."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class OnboardingProgress(Base):
    """
    Tracks a user's onboarding progress.

    Stores their role selection, completed steps, and preferences.
    """
    __tablename__ = "onboarding_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)

    # Role selection
    business_role = Column(SQLEnum(UserRole), nullable=True)

    # Overall status
    status = Column(SQLEnum(OnboardingStatus), default=OnboardingStatus.NOT_STARTED)

    # Step completion flags
    role_selected = Column(Boolean, default=False)
    first_source_connected = Column(Boolean, default=False)
    first_destination_connected = Column(Boolean, default=False)
    first_pipeline_created = Column(Boolean, default=False)
    first_pipeline_run = Column(Boolean, default=False)
    dashboard_viewed = Column(Boolean, default=False)
    ai_assistant_used = Column(Boolean, default=False)
    team_member_invited = Column(Boolean, default=False)

    # Preferences
    preferred_sources = Column(JSON, default=list)  # Source types user is interested in
    skip_reason = Column(String(255), nullable=True)  # If they skipped onboarding

    # Timestamps
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", backref="onboarding_progress")
    organization = relationship("Organization", backref="onboarding_progress")

    @property
    def completion_percentage(self) -> int:
        """Calculate onboarding completion percentage."""
        steps = [
            self.role_selected,
            self.first_source_connected,
            self.first_destination_connected,
            self.first_pipeline_created,
            self.first_pipeline_run,
            self.dashboard_viewed,
        ]
        completed = sum(1 for s in steps if s)
        return int((completed / len(steps)) * 100)

    @property
    def next_step(self) -> str:
        """Get the next recommended step."""
        if not self.role_selected:
            return "select_role"
        if not self.first_source_connected:
            return "connect_source"
        if not self.first_destination_connected:
            return "connect_destination"
        if not self.first_pipeline_created:
            return "create_pipeline"
        if not self.first_pipeline_run:
            return "run_pipeline"
        if not self.dashboard_viewed:
            return "view_dashboard"
        return "completed"
