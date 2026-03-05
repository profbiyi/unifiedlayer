"""
Dashboard Service.

Manages dashboard templates, user dashboards, and widget data retrieval.
Also provides industry-specific template instantiation (Feature B).
"""
import copy
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.models.pipeline import DataSource
from backend.templates.dashboard_templates import (
    get_available_templates_for_sources,
    get_dashboard_template_by_id,
    get_all_industry_templates,
    get_industry_template_by_id,
    recommend_industry_template as _recommend_template_fn,
)

logger = logging.getLogger(__name__)


class DashboardService:
    """Service for managing dashboards and executing widget queries."""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Existing template methods
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Feature B: Industry-Specific Template Methods
    # ------------------------------------------------------------------

    def get_industry_templates(self) -> List[Dict[str, Any]]:
        """
        Return a summary list of all five industry-specific dashboard templates.

        Each item contains metadata (id, name, description, icon, widget_count)
        but not the full widget SQL definitions.
        """
        return get_all_industry_templates()

    def create_dashboard_from_industry_template(
        self,
        org_id: int,
        template_id: str,
        data_source_id: int,
    ) -> Dict[str, Any]:
        """
        Instantiate an industry template as a populated dashboard object for an org.

        Resolves {transactions_table}, {orders_table}, {invoices_table} and
        {subscriptions_table} placeholders based on the data source's connector type,
        deriving the destination table names using dlt's ``<source_type>__<entity>``
        naming convention.

        The returned dict is ready to be returned directly from the API or stored.
        It is NOT automatically persisted; the route handler decides that.

        Args:
            org_id:         Organization ID (for ownership validation).
            template_id:    Industry template ID (e.g. "ecommerce").
            data_source_id: The DataSource.id whose connector type drives table names.

        Returns:
            Instantiated dashboard dict with resolved SQL in each widget.

        Raises:
            ValueError: If template or data source is not found / mismatched.
        """
        template = get_industry_template_by_id(template_id)
        if template is None:
            raise ValueError(f"Industry template '{template_id}' not found")

        source = (
            self.db.query(DataSource)
            .filter(
                DataSource.id == data_source_id,
                DataSource.organization_id == org_id,
                DataSource.is_active == True,  # noqa: E712
            )
            .first()
        )
        if source is None:
            raise ValueError(
                f"DataSource {data_source_id} not found or does not belong to org {org_id}"
            )

        source_type_str: str = (
            source.source_type.value
            if hasattr(source.source_type, "value")
            else str(source.source_type)
        ).lower()

        # Build table name map for this source type (validated whitelist)
        table_map = self._build_table_name_map(source_type_str)

        # Deep-copy template so we never mutate the registry
        dashboard = copy.deepcopy(template)

        # Resolve SQL placeholders in every widget
        resolved_widgets = []
        for widget in dashboard.get("widgets", []):
            raw_sql: str = widget.get("sql_template", "")
            for placeholder, table_name in table_map.items():
                raw_sql = raw_sql.replace(f"{{{placeholder}}}", table_name)
            widget["sql_template"] = raw_sql
            widget["resolved"] = True
            resolved_widgets.append(widget)

        dashboard["widgets"] = resolved_widgets
        dashboard["org_id"] = org_id
        dashboard["data_source_id"] = data_source_id
        dashboard["source_type"] = source_type_str
        dashboard["instantiated_at"] = datetime.now(timezone.utc).isoformat()

        return dashboard

    def recommend_industry_template(self, org_id: int) -> Optional[str]:
        """
        Examine the org's connected data sources and recommend the most
        relevant industry dashboard template ID.

        Scoring is based on how many of each template's
        ``recommended_for_source_types`` match the org's actual connected sources.

        Returns:
            Template ID string (e.g. "ecommerce") or None if no match.
        """
        sources = (
            self.db.query(DataSource)
            .filter(
                DataSource.organization_id == org_id,
                DataSource.is_active == True,  # noqa: E712
            )
            .all()
        )

        source_types: List[str] = [
            (
                s.source_type.value
                if hasattr(s.source_type, "value")
                else str(s.source_type)
            )
            for s in sources
        ]

        return _recommend_template_fn(source_types)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_table_name_map(source_type: str) -> Dict[str, str]:
        """
        Return a mapping of SQL placeholder names to actual destination table names
        for the given connector source_type.

        Table names follow the dlt convention: ``<source_type>__<entity>``
        (double underscore as separator).

        Only placeholder names from a strict whitelist are accepted to prevent
        template injection from polluting widget SQL.

        Args:
            source_type: Lowercase connector name (e.g. "stripe", "xero").

        Returns:
            Dict[placeholder_name, table_name]

        Raises:
            ValueError: If source_type contains non-alphanumeric/underscore characters.
        """
        # Safety: reject source_type strings that look suspicious
        if not re.match(r'^[a-z0-9_]+$', source_type):
            raise ValueError(f"Invalid source_type for table resolution: {source_type!r}")

        # Allowed placeholder names (hard whitelist — adding new ones requires code change)
        PLACEHOLDER_WHITELIST = frozenset({
            "transactions_table",
            "orders_table",
            "invoices_table",
            "subscriptions_table",
            "customers_table",
            "products_table",
        })

        prefix = source_type

        # Per-connector table name maps
        source_table_maps: Dict[str, Dict[str, str]] = {
            "stripe": {
                "transactions_table":  f"{prefix}__charges",
                "orders_table":        f"{prefix}__payment_intents",
                "subscriptions_table": f"{prefix}__subscriptions",
                "customers_table":     f"{prefix}__customers",
                "invoices_table":      f"{prefix}__invoices",
                "products_table":      f"{prefix}__products",
            },
            "paystack": {
                "transactions_table":  f"{prefix}__transactions",
                "orders_table":        f"{prefix}__transactions",
                "subscriptions_table": f"{prefix}__subscriptions",
                "customers_table":     f"{prefix}__customers",
                "invoices_table":      f"{prefix}__invoices",
                "products_table":      f"{prefix}__plans",
            },
            "xero": {
                "transactions_table":  f"{prefix}__bank_transactions",
                "orders_table":        f"{prefix}__purchase_orders",
                "invoices_table":      f"{prefix}__invoices",
                "subscriptions_table": f"{prefix}__invoices",  # repeating invoices proxy
                "customers_table":     f"{prefix}__contacts",
                "products_table":      f"{prefix}__items",
            },
            "quickbooks": {
                "transactions_table":  f"{prefix}__transactions",
                "orders_table":        f"{prefix}__purchase_orders",
                "invoices_table":      f"{prefix}__invoices",
                "subscriptions_table": f"{prefix}__recurring_transactions",
                "customers_table":     f"{prefix}__customers",
                "products_table":      f"{prefix}__items",
            },
            "freeagent": {
                "transactions_table":  f"{prefix}__bank_transactions",
                "orders_table":        f"{prefix}__invoices",
                "invoices_table":      f"{prefix}__invoices",
                "subscriptions_table": f"{prefix}__invoices",
                "customers_table":     f"{prefix}__contacts",
                "products_table":      f"{prefix}__projects",
            },
            "sage": {
                "transactions_table":  f"{prefix}__transactions",
                "orders_table":        f"{prefix}__sales_invoices",
                "invoices_table":      f"{prefix}__sales_invoices",
                "subscriptions_table": f"{prefix}__recurring_invoices",
                "customers_table":     f"{prefix}__contacts",
                "products_table":      f"{prefix}__products",
            },
            "flutterwave": {
                "transactions_table":  f"{prefix}__transactions",
                "orders_table":        f"{prefix}__transactions",
                "subscriptions_table": f"{prefix}__subscriptions",
                "customers_table":     f"{prefix}__customers",
                "invoices_table":      f"{prefix}__transactions",
                "products_table":      f"{prefix}__plans",
            },
            "mono": {
                "transactions_table":  f"{prefix}__transactions",
                "orders_table":        f"{prefix}__transactions",
                "invoices_table":      f"{prefix}__transactions",
                "subscriptions_table": f"{prefix}__transactions",
                "customers_table":     f"{prefix}__accounts",
                "products_table":      f"{prefix}__transactions",
            },
        }

        # Default fallback for unknown connectors
        default_map: Dict[str, str] = {
            "transactions_table":  f"{prefix}__transactions",
            "orders_table":        f"{prefix}__orders",
            "invoices_table":      f"{prefix}__invoices",
            "subscriptions_table": f"{prefix}__subscriptions",
            "customers_table":     f"{prefix}__customers",
            "products_table":      f"{prefix}__products",
        }

        table_map = source_table_maps.get(source_type, default_map)

        # Assert only whitelisted keys are present (belt-and-suspenders)
        for key in table_map:
            if key not in PLACEHOLDER_WHITELIST:
                raise ValueError(f"Table map contains disallowed placeholder: {key!r}")

        return table_map


def get_dashboard_service(db: Session) -> DashboardService:
    """Factory function for DashboardService."""
    return DashboardService(db)
