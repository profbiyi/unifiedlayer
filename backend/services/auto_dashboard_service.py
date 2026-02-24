"""
Auto Dashboard Service.

Automatically creates dashboards when users connect their first data source.
Maps source types to appropriate dashboard templates and creates pre-configured widgets.
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from sqlalchemy.orm import Session

from backend.models.pipeline import DataSource, Organization
from backend.templates.dashboard_templates import (
    DASHBOARD_TEMPLATES,
    get_dashboard_template_by_id,
)

logger = logging.getLogger(__name__)


# Mapping of source types to their recommended dashboard templates
# Each source type maps to a list of templates in order of priority
SOURCE_TO_DASHBOARD_MAPPING: Dict[str, List[str]] = {
    # Payment processors -> Revenue and Payment analytics
    "stripe": ["revenue_overview", "payment_analytics"],
    "paystack": ["payment_analytics", "revenue_overview"],
    "flutterwave": ["payment_analytics"],
    "gocardless": ["payment_analytics"],

    # Accounting software -> Invoice and Cash Flow
    "xero": ["invoice_health", "cash_flow"],
    "quickbooks": ["invoice_health", "cash_flow"],
    "sage": ["invoice_health"],
    "freeagent": ["invoice_health"],

    # Banking -> Cash Flow
    "mono": ["cash_flow"],
    "truelayer": ["cash_flow"],
    "open_banking": ["cash_flow"],

    # Databases -> Custom data overview (no pre-built template)
    "postgres": [],
    "mysql": [],
    "mongodb": [],
}


class AutoDashboardService:
    """Service for automatically creating dashboards based on connected sources."""

    def __init__(self, db: Session):
        self.db = db

    def is_first_source_for_org(self, org_id: int) -> bool:
        """
        Check if this is the first source for the organization.

        Args:
            org_id: Organization ID

        Returns:
            True if no active sources exist for the org
        """
        source_count = self.db.query(DataSource).filter(
            DataSource.organization_id == org_id,
            DataSource.is_active == True,
        ).count()

        # Return True if this is the first source (count is 0 or 1 - since the
        # new source may already be created when this is called)
        return source_count <= 1

    def get_dashboard_templates_for_source(
        self,
        source_type: str
    ) -> List[Dict[str, Any]]:
        """
        Get the recommended dashboard templates for a source type.

        Args:
            source_type: The type of data source (e.g., 'stripe', 'xero')

        Returns:
            List of dashboard template details
        """
        source_type_lower = source_type.lower()
        template_ids = SOURCE_TO_DASHBOARD_MAPPING.get(source_type_lower, [])

        templates = []
        for template_id in template_ids:
            template = get_dashboard_template_by_id(template_id)
            if template:
                templates.append(template)

        return templates

    def create_auto_dashboard(
        self,
        org_id: int,
        source: DataSource,
    ) -> Optional[Dict[str, Any]]:
        """
        Create an auto-dashboard for a newly connected source.

        This creates a dashboard configuration based on the source type.
        The dashboard is stored in memory/cache for the user to view.

        Args:
            org_id: Organization ID
            source: The newly connected DataSource

        Returns:
            Dashboard configuration dict or None if no template available
        """
        source_type = source.source_type.value if hasattr(source.source_type, 'value') else str(source.source_type)
        templates = self.get_dashboard_templates_for_source(source_type)

        if not templates:
            logger.info(
                f"No dashboard template available for source type: {source_type}"
            )
            return None

        # Use the first (primary) template
        template = templates[0]

        # Create dashboard configuration
        dashboard = {
            "id": str(uuid4()),
            "template_id": template["id"],
            "name": template["name"],
            "description": template["description"],
            "category": template["category"],
            "icon": template["icon"],
            "source_id": str(source.public_id),
            "source_type": source_type,
            "source_name": source.name,
            "organization_id": org_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "auto_created": True,
            "widgets": self._prepare_widgets(template, source),
        }

        logger.info(
            f"Auto-created dashboard '{dashboard['name']}' for source "
            f"'{source.name}' (org_id={org_id})"
        )

        return dashboard

    def _prepare_widgets(
        self,
        template: Dict[str, Any],
        source: DataSource,
    ) -> List[Dict[str, Any]]:
        """
        Prepare widget configurations for the dashboard.

        Replaces template placeholders with actual source details.

        Args:
            template: Dashboard template
            source: Data source

        Returns:
            List of prepared widget configurations
        """
        source_type = source.source_type.value if hasattr(source.source_type, 'value') else str(source.source_type)
        table_prefix = self._get_table_prefix(source_type)

        widgets = []
        for widget in template.get("widgets", []):
            widget_copy = widget.copy()

            # Replace table placeholder in SQL template
            if "sql_template" in widget_copy:
                widget_copy["sql_template"] = widget_copy["sql_template"].replace(
                    "{source_table}",
                    table_prefix
                )

            # Add source metadata
            widget_copy["source_id"] = str(source.public_id)
            widget_copy["source_type"] = source_type

            widgets.append(widget_copy)

        return widgets

    def _get_table_prefix(self, source_type: str) -> str:
        """
        Get the table prefix for a source type.

        Args:
            source_type: Source type string

        Returns:
            Table prefix for SQL queries
        """
        prefix_map = {
            "stripe": "stripe",
            "paystack": "paystack",
            "xero": "xero",
            "quickbooks": "qb",
            "sage": "sage",
            "freeagent": "freeagent",
            "mono": "mono",
            "truelayer": "truelayer",
            "open_banking": "truelayer",
            "flutterwave": "flutterwave",
            "gocardless": "gocardless",
        }
        return prefix_map.get(source_type.lower(), source_type.lower())

    def should_create_auto_dashboard(
        self,
        org_id: int,
        source_type: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Determine if an auto-dashboard should be created.

        Args:
            org_id: Organization ID
            source_type: Type of the data source

        Returns:
            Tuple of (should_create, reason)
        """
        # Check if templates exist for this source type
        templates = self.get_dashboard_templates_for_source(source_type)
        if not templates:
            return False, "no_template_available"

        # Check if this is the first source of this type for the org
        source_type_lower = source_type.lower()
        existing_sources = self.db.query(DataSource).filter(
            DataSource.organization_id == org_id,
            DataSource.is_active == True,
        ).all()

        # Check if any existing source matches the same template set
        for existing in existing_sources:
            existing_type = existing.source_type.value if hasattr(existing.source_type, 'value') else str(existing.source_type)
            existing_templates = SOURCE_TO_DASHBOARD_MAPPING.get(existing_type.lower(), [])
            new_templates = SOURCE_TO_DASHBOARD_MAPPING.get(source_type_lower, [])

            # If they share a template, don't create a duplicate
            if set(existing_templates) & set(new_templates):
                return False, "similar_dashboard_exists"

        return True, None

    def get_auto_dashboard_notification(
        self,
        dashboard: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Generate notification data for the auto-created dashboard.

        Args:
            dashboard: The auto-created dashboard

        Returns:
            Notification configuration dict
        """
        template_messages = {
            "revenue_overview": {
                "title": "Revenue Dashboard Ready!",
                "message": f"We created a Revenue Overview dashboard for your {dashboard.get('source_name', 'source')}. Track your MRR, growth, and top customers.",
                "cta": "View Dashboard",
            },
            "payment_analytics": {
                "title": "Payment Analytics Ready!",
                "message": f"We created a Payment Analytics dashboard for your {dashboard.get('source_name', 'source')}. Monitor success rates and transaction volumes.",
                "cta": "View Dashboard",
            },
            "invoice_health": {
                "title": "Invoice Dashboard Ready!",
                "message": f"We created an Invoice Health dashboard for your {dashboard.get('source_name', 'source')}. Track outstanding invoices and aging.",
                "cta": "View Dashboard",
            },
            "cash_flow": {
                "title": "Cash Flow Dashboard Ready!",
                "message": f"We created a Cash Flow dashboard for your {dashboard.get('source_name', 'source')}. Monitor inflows, outflows, and runway.",
                "cta": "View Dashboard",
            },
        }

        template_id = dashboard.get("template_id", "")
        notification = template_messages.get(template_id, {
            "title": "Dashboard Ready!",
            "message": f"We created a dashboard for your {dashboard.get('source_name', 'source')}.",
            "cta": "View Dashboard",
        })

        return {
            "type": "auto_dashboard_created",
            "dashboard_id": dashboard.get("id"),
            "template_id": template_id,
            "dashboard_name": dashboard.get("name"),
            "dashboard_url": f"/dashboards/templates/{template_id}/data",
            **notification,
        }


def get_auto_dashboard_service(db: Session) -> AutoDashboardService:
    """Factory function for AutoDashboardService."""
    return AutoDashboardService(db)
