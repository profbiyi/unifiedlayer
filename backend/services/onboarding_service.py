"""
Onboarding Service.

Manages user onboarding flow, recommendations, and progress tracking.
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.models.onboarding import OnboardingProgress, OnboardingStatus, UserRole
from backend.models.pipeline import DataSource, Destination, Pipeline, PipelineRun

logger = logging.getLogger(__name__)


# Role-based source recommendations
ROLE_SOURCE_RECOMMENDATIONS = {
    UserRole.FOUNDER: [
        {
            "type": "stripe",
            "name": "Stripe",
            "reason": "Track revenue, MRR, and customer metrics",
            "priority": 1,
        },
        {
            "type": "paystack",
            "name": "Paystack",
            "reason": "Monitor African market transactions",
            "priority": 2,
        },
        {
            "type": "xero",
            "name": "Xero",
            "reason": "Get full financial visibility",
            "priority": 3,
        },
        {
            "type": "quickbooks",
            "name": "QuickBooks",
            "reason": "Sync accounting data for insights",
            "priority": 4,
        },
    ],
    UserRole.FINANCE: [
        {
            "type": "xero",
            "name": "Xero",
            "reason": "Automate invoice and expense tracking",
            "priority": 1,
        },
        {
            "type": "quickbooks",
            "name": "QuickBooks",
            "reason": "Sync all accounting transactions",
            "priority": 2,
        },
        {
            "type": "stripe",
            "name": "Stripe",
            "reason": "Reconcile payment data",
            "priority": 3,
        },
        {
            "type": "mono",
            "name": "Mono (Nigerian Banks)",
            "reason": "Automate bank reconciliation",
            "priority": 4,
        },
    ],
    UserRole.OPERATIONS: [
        {
            "type": "postgres",
            "name": "PostgreSQL",
            "reason": "Replicate production data for analytics",
            "priority": 1,
        },
        {
            "type": "mysql",
            "name": "MySQL",
            "reason": "Sync operational databases",
            "priority": 2,
        },
        {
            "type": "mongodb",
            "name": "MongoDB",
            "reason": "Flatten NoSQL data for reporting",
            "priority": 3,
        },
    ],
    UserRole.SALES: [
        {
            "type": "stripe",
            "name": "Stripe",
            "reason": "Track sales and customer lifetime value",
            "priority": 1,
        },
        {
            "type": "paystack",
            "name": "Paystack",
            "reason": "Monitor sales in African markets",
            "priority": 2,
        },
    ],
    UserRole.DEVELOPER: [
        {
            "type": "postgres",
            "name": "PostgreSQL",
            "reason": "Set up data warehouse replication",
            "priority": 1,
        },
        {
            "type": "mysql",
            "name": "MySQL",
            "reason": "Sync application databases",
            "priority": 2,
        },
        {
            "type": "mongodb",
            "name": "MongoDB",
            "reason": "ETL from NoSQL sources",
            "priority": 3,
        },
    ],
    UserRole.OTHER: [
        {
            "type": "stripe",
            "name": "Stripe",
            "reason": "Start with payment data",
            "priority": 1,
        },
        {
            "type": "postgres",
            "name": "PostgreSQL",
            "reason": "Connect your database",
            "priority": 2,
        },
    ],
}

# Role-based dashboard recommendations
ROLE_DASHBOARD_RECOMMENDATIONS = {
    UserRole.FOUNDER: ["revenue_overview", "cash_flow"],
    UserRole.FINANCE: ["invoice_health", "cash_flow"],
    UserRole.OPERATIONS: [],
    UserRole.SALES: ["revenue_overview", "payment_analytics"],
    UserRole.DEVELOPER: [],
    UserRole.OTHER: ["revenue_overview"],
}


class OnboardingService:
    """Service for managing user onboarding."""

    def __init__(self, db: Session):
        self.db = db

    def get_or_create_progress(self, user_id: int, org_id: int) -> OnboardingProgress:
        """Get or create onboarding progress for a user."""
        progress = self.db.query(OnboardingProgress).filter(
            OnboardingProgress.user_id == user_id
        ).first()

        if not progress:
            progress = OnboardingProgress(
                user_id=user_id,
                organization_id=org_id,
                status=OnboardingStatus.NOT_STARTED,
            )
            self.db.add(progress)
            self.db.commit()
            self.db.refresh(progress)

        return progress

    def get_progress(self, user_id: int) -> Optional[OnboardingProgress]:
        """Get onboarding progress for a user."""
        return self.db.query(OnboardingProgress).filter(
            OnboardingProgress.user_id == user_id
        ).first()

    def set_role(self, user_id: int, org_id: int, role: UserRole) -> OnboardingProgress:
        """Set the user's business role."""
        progress = self.get_or_create_progress(user_id, org_id)

        progress.business_role = role
        progress.role_selected = True
        progress.status = OnboardingStatus.IN_PROGRESS
        progress.started_at = progress.started_at or datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(progress)

        return progress

    def get_source_recommendations(self, user_id: int) -> List[Dict[str, Any]]:
        """Get source recommendations based on user's role."""
        progress = self.get_progress(user_id)

        if not progress or not progress.business_role:
            # Default recommendations
            return ROLE_SOURCE_RECOMMENDATIONS.get(UserRole.OTHER, [])

        return ROLE_SOURCE_RECOMMENDATIONS.get(progress.business_role, [])

    def get_dashboard_recommendations(self, user_id: int) -> List[str]:
        """Get dashboard template recommendations based on user's role."""
        progress = self.get_progress(user_id)

        if not progress or not progress.business_role:
            return ROLE_DASHBOARD_RECOMMENDATIONS.get(UserRole.OTHER, [])

        return ROLE_DASHBOARD_RECOMMENDATIONS.get(progress.business_role, [])

    def mark_step_complete(self, user_id: int, step: str) -> OnboardingProgress:
        """Mark an onboarding step as complete."""
        progress = self.get_progress(user_id)
        if not progress:
            return None

        step_mapping = {
            "role_selected": "role_selected",
            "first_source_connected": "first_source_connected",
            "first_destination_connected": "first_destination_connected",
            "first_pipeline_created": "first_pipeline_created",
            "first_pipeline_run": "first_pipeline_run",
            "dashboard_viewed": "dashboard_viewed",
            "ai_assistant_used": "ai_assistant_used",
            "team_member_invited": "team_member_invited",
        }

        if step in step_mapping:
            setattr(progress, step_mapping[step], True)

        # Check if all core steps are complete
        if all([
            progress.role_selected,
            progress.first_source_connected,
            progress.first_pipeline_created,
            progress.first_pipeline_run,
        ]):
            progress.status = OnboardingStatus.COMPLETED
            progress.completed_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(progress)

        return progress

    def sync_progress_from_data(self, user_id: int, org_id: int) -> OnboardingProgress:
        """
        Sync onboarding progress based on actual data in the system.

        This is useful for users who might have skipped onboarding but
        already have data set up.
        """
        progress = self.get_or_create_progress(user_id, org_id)

        # Check for sources
        sources = self.db.query(DataSource).filter(
            DataSource.organization_id == org_id,
            DataSource.is_active,
        ).count()
        if sources > 0:
            progress.first_source_connected = True

        # Check for destinations
        destinations = self.db.query(Destination).filter(
            Destination.organization_id == org_id,
            Destination.is_active,
        ).count()
        if destinations > 0:
            progress.first_destination_connected = True

        # Check for pipelines
        pipelines = self.db.query(Pipeline).filter(
            Pipeline.organization_id == org_id,
        ).count()
        if pipelines > 0:
            progress.first_pipeline_created = True

        # Check for pipeline runs
        runs = self.db.query(PipelineRun).join(Pipeline).filter(
            Pipeline.organization_id == org_id,
        ).count()
        if runs > 0:
            progress.first_pipeline_run = True

        self.db.commit()
        self.db.refresh(progress)

        return progress

    def skip_onboarding(self, user_id: int, reason: Optional[str] = None) -> OnboardingProgress:
        """Skip the onboarding flow."""
        progress = self.get_progress(user_id)
        if not progress:
            return None

        progress.status = OnboardingStatus.SKIPPED
        progress.skip_reason = reason
        progress.completed_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(progress)

        return progress

    def get_checklist(self, user_id: int, org_id: int) -> Dict[str, Any]:
        """Get the onboarding checklist with completion status."""
        progress = self.sync_progress_from_data(user_id, org_id)

        checklist = [
            {
                "id": "role_selected",
                "title": "Select your role",
                "description": "Tell us about your role to personalize your experience",
                "completed": progress.role_selected,
                "href": "/onboarding",
            },
            {
                "id": "first_source_connected",
                "title": "Connect your first data source",
                "description": "Connect Stripe, Xero, or another data source",
                "completed": progress.first_source_connected,
                "href": "/sources/new",
            },
            {
                "id": "first_destination_connected",
                "title": "Set up a destination",
                "description": "Where should we send your data?",
                "completed": progress.first_destination_connected,
                "href": "/destinations/new",
            },
            {
                "id": "first_pipeline_created",
                "title": "Create your first pipeline",
                "description": "Set up automated data sync",
                "completed": progress.first_pipeline_created,
                "href": "/pipelines/new",
            },
            {
                "id": "first_pipeline_run",
                "title": "Run your first sync",
                "description": "See your data flowing",
                "completed": progress.first_pipeline_run,
                "href": "/pipelines",
            },
            {
                "id": "ai_assistant_used",
                "title": "Ask AI a question",
                "description": "Try our AI assistant to explore your data",
                "completed": progress.ai_assistant_used,
                "href": "/ask",
            },
        ]

        return {
            "status": progress.status.value,
            "completion_percentage": progress.completion_percentage,
            "next_step": progress.next_step,
            "business_role": progress.business_role.value if progress.business_role else None,
            "checklist": checklist,
        }


def get_onboarding_service(db: Session) -> OnboardingService:
    """Factory function for OnboardingService."""
    return OnboardingService(db)
