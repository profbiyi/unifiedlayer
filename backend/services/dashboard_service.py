"""
Dashboard Service.

Manages dashboard templates, user dashboards, and widget data retrieval.
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.models.pipeline import DataSource
from backend.templates.dashboard_templates import (
    get_available_templates_for_sources,
    get_dashboard_template_by_id,
)

logger = logging.getLogger(__name__)


class DashboardService:
    """Service for managing dashboards and executing widget queries."""

    def __init__(self, db: Session):
        self.db = db

    def get_available_templates(self, org_id: int) -> List[Dict[str, Any]]:
        """
        Get all dashboard templates with availability status based on connected sources.

        Args:
            org_id: Organization ID

        Returns:
            List of templates with 'available' flag
        """
        # Get connected source types for this org
        sources = self.db.query(DataSource).filter(
            DataSource.organization_id == org_id,
            DataSource.is_active,
        ).all()

        source_types = [s.source_type for s in sources]

        return get_available_templates_for_sources(source_types)

    def get_template_details(self, template_id: str) -> Optional[Dict[str, Any]]:
        """
        Get full template details including widgets.

        Args:
            template_id: Template ID

        Returns:
            Template dict or None
        """
        return get_dashboard_template_by_id(template_id)

    def check_template_requirements(
        self,
        org_id: int,
        template_id: str
    ) -> Dict[str, Any]:
        """
        Check what's needed to use a template.

        Args:
            org_id: Organization ID
            template_id: Template ID

        Returns:
            Dict with 'can_use', 'connected_sources', 'missing_sources'
        """
        template = get_dashboard_template_by_id(template_id)
        if not template:
            return {"error": "Template not found"}

        # Get connected sources
        sources = self.db.query(DataSource).filter(
            DataSource.organization_id == org_id,
            DataSource.is_active,
        ).all()

        connected_types = {s.source_type.lower() for s in sources}
        required_sources = [s.lower() for s in template["required_sources"]]

        # Check if any required source is connected (OR condition)
        connected = [s for s in required_sources if s in connected_types]
        missing = [s for s in required_sources if s not in connected_types]

        return {
            "can_use": len(connected) > 0,
            "connected_sources": connected,
            "missing_sources": missing if len(connected) == 0 else [],
            "required_sources": required_sources,
        }

    def get_source_table_prefix(self, org_id: int, source_type: str) -> Optional[str]:
        """
        Get the table prefix for a source type.

        Different sources may store data in tables with different naming conventions.
        This returns the appropriate prefix for SQL templates.
        """
        # For now, use simple naming convention
        # In production, you might query metadata about actual table names
        source_type_lower = source_type.lower()

        # Map source types to their table prefixes
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
        }

        return prefix_map.get(source_type_lower, source_type_lower)

    def execute_widget_query(
        self,
        org_id: int,
        sql_template: str,
        source_type: str,
        timeout_seconds: int = 30,
    ) -> Dict[str, Any]:
        """
        Execute a widget SQL query and return results.

        Args:
            org_id: Organization ID
            sql_template: SQL template with {source_table} placeholder
            source_type: Source type to determine table prefix
            timeout_seconds: Query timeout

        Returns:
            Dict with 'data', 'columns', 'row_count'
        """
        try:
            # Get table prefix
            table_prefix = self.get_source_table_prefix(org_id, source_type)

            # Replace placeholder in SQL
            sql = sql_template.replace("{source_table}", table_prefix)

            # Execute query with timeout
            result = self.db.execute(
                text(f"SET statement_timeout = '{timeout_seconds * 1000}'; {sql}")
            )

            rows = result.fetchall()
            columns = list(result.keys()) if rows else []

            # Convert to list of dicts
            data = [dict(zip(columns, row)) for row in rows]

            return {
                "data": data,
                "columns": columns,
                "row_count": len(data),
            }

        except Exception as e:
            logger.error(f"Widget query failed: {e}")
            return {
                "error": str(e),
                "data": [],
                "columns": [],
                "row_count": 0,
            }

    def get_dashboard_data(
        self,
        org_id: int,
        template_id: str,
        source_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get all widget data for a dashboard template.

        Args:
            org_id: Organization ID
            template_id: Template ID
            source_type: Optional specific source to use

        Returns:
            Template with populated widget data
        """
        template = get_dashboard_template_by_id(template_id)
        if not template:
            return {"error": "Template not found"}

        # Determine which source to use
        if not source_type:
            # Get first connected source that matches template requirements
            sources = self.db.query(DataSource).filter(
                DataSource.organization_id == org_id,
                DataSource.is_active,
                DataSource.source_type.in_(template["required_sources"]),
            ).first()

            if sources:
                source_type = sources.source_type
            else:
                return {"error": "No compatible source connected"}

        # Execute each widget query
        widgets_with_data = []
        for widget in template["widgets"]:
            widget_copy = widget.copy()

            if "sql_template" in widget:
                query_result = self.execute_widget_query(
                    org_id=org_id,
                    sql_template=widget["sql_template"],
                    source_type=source_type,
                )
                widget_copy["data"] = query_result.get("data", [])
                widget_copy["error"] = query_result.get("error")

            widgets_with_data.append(widget_copy)

        return {
            "id": template["id"],
            "name": template["name"],
            "description": template["description"],
            "category": template["category"],
            "source_type": source_type,
            "widgets": widgets_with_data,
            "refreshed_at": datetime.now(timezone.utc).isoformat(),
        }


def get_dashboard_service(db: Session) -> DashboardService:
    """Factory function for DashboardService."""
    return DashboardService(db)
