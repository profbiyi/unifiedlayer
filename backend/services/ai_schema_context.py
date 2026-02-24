"""
AI Schema Context Service.

Builds schema context for the LLM to understand available tables and columns.
"""
import logging
from typing import Any, Dict
from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import Session

from backend.models.pipeline import DataSource

logger = logging.getLogger(__name__)

# Cache for schema context (org_id -> (timestamp, context))
_schema_cache: Dict[int, tuple] = {}
CACHE_TTL_SECONDS = 300  # 5 minutes


class SchemaContextService:
    """
    Service for building schema context for AI queries.

    Discovers available tables and columns from connected sources
    and formats them for LLM consumption.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_org_schema(self, org_id: int) -> Dict[str, Any]:
        """
        Get all tables and columns available to an organization.

        Returns:
            Dict mapping table names to their schema info:
            {
                "stripe_payments": {
                    "columns": [
                        {"name": "id", "type": "varchar", "description": "Payment ID"},
                        {"name": "amount", "type": "integer", "description": "Amount in cents"},
                        ...
                    ],
                    "source": "stripe",
                    "row_count": 1500,
                    "description": "Stripe payment transactions"
                },
                ...
            }
        """
        # Check cache
        if org_id in _schema_cache:
            timestamp, cached_schema = _schema_cache[org_id]
            if datetime.now(timezone.utc) - timestamp < timedelta(seconds=CACHE_TTL_SECONDS):
                return cached_schema

        schema = {}

        # Get connected sources
        sources = self.db.query(DataSource).filter(
            DataSource.organization_id == org_id,
            DataSource.is_active,
        ).all()

        for source in sources:
            source_tables = self._get_source_tables(source)
            schema.update(source_tables)

        # Cache the result
        _schema_cache[org_id] = (datetime.now(timezone.utc), schema)

        return schema

    def _get_source_tables(self, source: DataSource) -> Dict[str, Any]:
        """
        Get table schemas for a specific source.

        This is a simplified implementation that uses known table structures
        for each connector type. In production, you would query the actual
        warehouse metadata.
        """
        source_type = source.source_type.lower()
        prefix = self._get_table_prefix(source_type)

        # Known table structures for each source type
        table_schemas = {
            "stripe": {
                f"{prefix}_payments": {
                    "columns": [
                        {"name": "id", "type": "varchar", "description": "Payment ID"},
                        {"name": "amount", "type": "integer", "description": "Amount in cents"},
                        {"name": "currency", "type": "varchar", "description": "3-letter currency code"},
                        {"name": "status", "type": "varchar", "description": "Payment status (succeeded, failed, pending)"},
                        {"name": "customer_id", "type": "varchar", "description": "Customer ID"},
                        {"name": "customer_email", "type": "varchar", "description": "Customer email"},
                        {"name": "payment_method_type", "type": "varchar", "description": "Payment method (card, bank_transfer)"},
                        {"name": "created_at", "type": "timestamp", "description": "Payment creation time"},
                        {"name": "refunded", "type": "boolean", "description": "Whether payment was refunded"},
                        {"name": "failure_code", "type": "varchar", "description": "Failure reason code"},
                        {"name": "failure_message", "type": "varchar", "description": "Failure description"},
                    ],
                    "source": "stripe",
                    "description": "Stripe payment transactions",
                },
                f"{prefix}_customers": {
                    "columns": [
                        {"name": "id", "type": "varchar", "description": "Customer ID"},
                        {"name": "email", "type": "varchar", "description": "Customer email"},
                        {"name": "name", "type": "varchar", "description": "Customer name"},
                        {"name": "created_at", "type": "timestamp", "description": "Customer creation time"},
                    ],
                    "source": "stripe",
                    "description": "Stripe customers",
                },
                f"{prefix}_subscriptions": {
                    "columns": [
                        {"name": "id", "type": "varchar", "description": "Subscription ID"},
                        {"name": "customer_id", "type": "varchar", "description": "Customer ID"},
                        {"name": "status", "type": "varchar", "description": "Subscription status (active, canceled, past_due)"},
                        {"name": "amount", "type": "integer", "description": "Subscription amount in cents"},
                        {"name": "currency", "type": "varchar", "description": "Currency code"},
                        {"name": "current_period_start", "type": "timestamp", "description": "Current period start"},
                        {"name": "current_period_end", "type": "timestamp", "description": "Current period end"},
                        {"name": "canceled_at", "type": "timestamp", "description": "Cancellation time"},
                        {"name": "created_at", "type": "timestamp", "description": "Subscription creation time"},
                    ],
                    "source": "stripe",
                    "description": "Stripe subscriptions",
                },
            },
            "paystack": {
                f"{prefix}_transactions": {
                    "columns": [
                        {"name": "id", "type": "integer", "description": "Transaction ID"},
                        {"name": "reference", "type": "varchar", "description": "Transaction reference"},
                        {"name": "amount", "type": "integer", "description": "Amount in kobo/pesewas"},
                        {"name": "currency", "type": "varchar", "description": "Currency (NGN, GHS, KES)"},
                        {"name": "status", "type": "varchar", "description": "Transaction status (success, failed)"},
                        {"name": "customer_email", "type": "varchar", "description": "Customer email"},
                        {"name": "channel", "type": "varchar", "description": "Payment channel (card, bank, ussd)"},
                        {"name": "created_at", "type": "timestamp", "description": "Transaction time"},
                    ],
                    "source": "paystack",
                    "description": "Paystack transactions",
                },
                f"{prefix}_customers": {
                    "columns": [
                        {"name": "id", "type": "integer", "description": "Customer ID"},
                        {"name": "email", "type": "varchar", "description": "Customer email"},
                        {"name": "first_name", "type": "varchar", "description": "First name"},
                        {"name": "last_name", "type": "varchar", "description": "Last name"},
                        {"name": "created_at", "type": "timestamp", "description": "Customer creation time"},
                    ],
                    "source": "paystack",
                    "description": "Paystack customers",
                },
            },
            "xero": {
                f"{prefix}_invoices": {
                    "columns": [
                        {"name": "id", "type": "varchar", "description": "Invoice ID"},
                        {"name": "invoice_number", "type": "varchar", "description": "Invoice number"},
                        {"name": "contact_id", "type": "varchar", "description": "Contact/Customer ID"},
                        {"name": "customer_name", "type": "varchar", "description": "Customer name"},
                        {"name": "customer_email", "type": "varchar", "description": "Customer email"},
                        {"name": "status", "type": "varchar", "description": "Invoice status (draft, sent, paid, overdue)"},
                        {"name": "sub_total", "type": "decimal", "description": "Subtotal amount"},
                        {"name": "total_tax", "type": "decimal", "description": "Total tax amount"},
                        {"name": "total", "type": "decimal", "description": "Total amount"},
                        {"name": "amount_due", "type": "decimal", "description": "Amount due"},
                        {"name": "amount_paid", "type": "decimal", "description": "Amount paid"},
                        {"name": "currency", "type": "varchar", "description": "Currency code"},
                        {"name": "issued_date", "type": "date", "description": "Invoice date"},
                        {"name": "due_date", "type": "date", "description": "Due date"},
                        {"name": "paid_at", "type": "timestamp", "description": "Payment date"},
                    ],
                    "source": "xero",
                    "description": "Xero invoices",
                },
                f"{prefix}_bank_transactions": {
                    "columns": [
                        {"name": "id", "type": "varchar", "description": "Transaction ID"},
                        {"name": "type", "type": "varchar", "description": "Transaction type (credit, debit)"},
                        {"name": "amount", "type": "decimal", "description": "Transaction amount"},
                        {"name": "date", "type": "date", "description": "Transaction date"},
                        {"name": "description", "type": "varchar", "description": "Transaction description"},
                        {"name": "category", "type": "varchar", "description": "Category"},
                        {"name": "account_id", "type": "varchar", "description": "Bank account ID"},
                    ],
                    "source": "xero",
                    "description": "Xero bank transactions",
                },
            },
            "quickbooks": {
                f"{prefix}_invoices": {
                    "columns": [
                        {"name": "id", "type": "varchar", "description": "Invoice ID"},
                        {"name": "invoice_number", "type": "varchar", "description": "Invoice number"},
                        {"name": "customer_id", "type": "varchar", "description": "Customer ID"},
                        {"name": "customer_name", "type": "varchar", "description": "Customer name"},
                        {"name": "status", "type": "varchar", "description": "Invoice status"},
                        {"name": "total", "type": "decimal", "description": "Total amount"},
                        {"name": "balance_due", "type": "decimal", "description": "Balance due"},
                        {"name": "txn_date", "type": "date", "description": "Transaction date"},
                        {"name": "due_date", "type": "date", "description": "Due date"},
                    ],
                    "source": "quickbooks",
                    "description": "QuickBooks invoices",
                },
            },
            "mono": {
                f"{prefix}_transactions": {
                    "columns": [
                        {"name": "id", "type": "varchar", "description": "Transaction ID"},
                        {"name": "type", "type": "varchar", "description": "Transaction type (credit, debit)"},
                        {"name": "amount", "type": "decimal", "description": "Transaction amount"},
                        {"name": "narration", "type": "varchar", "description": "Transaction narration"},
                        {"name": "date", "type": "timestamp", "description": "Transaction date"},
                        {"name": "category", "type": "varchar", "description": "Category"},
                        {"name": "account_id", "type": "varchar", "description": "Account ID"},
                    ],
                    "source": "mono",
                    "description": "Mono bank transactions (Nigerian banks)",
                },
                f"{prefix}_accounts": {
                    "columns": [
                        {"name": "id", "type": "varchar", "description": "Account ID"},
                        {"name": "name", "type": "varchar", "description": "Account name"},
                        {"name": "account_number", "type": "varchar", "description": "Account number"},
                        {"name": "balance", "type": "decimal", "description": "Current balance"},
                        {"name": "currency", "type": "varchar", "description": "Currency (NGN)"},
                    ],
                    "source": "mono",
                    "description": "Mono bank accounts",
                },
            },
            "truelayer": {
                f"{prefix}_transactions": {
                    "columns": [
                        {"name": "id", "type": "varchar", "description": "Transaction ID"},
                        {"name": "amount", "type": "decimal", "description": "Transaction amount"},
                        {"name": "currency", "type": "varchar", "description": "Currency (GBP, EUR)"},
                        {"name": "description", "type": "varchar", "description": "Transaction description"},
                        {"name": "transaction_date", "type": "timestamp", "description": "Transaction date"},
                        {"name": "merchant_name", "type": "varchar", "description": "Merchant name"},
                        {"name": "merchant_category_code", "type": "varchar", "description": "MCC code"},
                        {"name": "merchant_category_name", "type": "varchar", "description": "Category name"},
                        {"name": "account_id", "type": "varchar", "description": "Account ID"},
                    ],
                    "source": "truelayer",
                    "description": "TrueLayer bank transactions (UK Open Banking)",
                },
            },
        }

        return table_schemas.get(source_type, {})

    def _get_table_prefix(self, source_type: str) -> str:
        """Get the table prefix for a source type."""
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
        return prefix_map.get(source_type, source_type)

    def build_llm_context(self, schema: Dict[str, Any]) -> str:
        """
        Build a concise schema description for the LLM prompt.

        Formats tables and columns in a way that's easy for the LLM to understand
        while being token-efficient.
        """
        if not schema:
            return "No tables available. Please connect a data source first."

        lines = ["Available tables and columns:\n"]

        for table_name, table_info in schema.items():
            description = table_info.get("description", "")
            lines.append(f"## {table_name}")
            if description:
                lines.append(f"   {description}")

            columns = table_info.get("columns", [])
            for col in columns:
                col_desc = f"   - {col['name']} ({col['type']})"
                if col.get("description"):
                    col_desc += f": {col['description']}"
                lines.append(col_desc)

            lines.append("")  # Empty line between tables

        return "\n".join(lines)

    def invalidate_cache(self, org_id: int) -> None:
        """Invalidate the schema cache for an organization."""
        if org_id in _schema_cache:
            del _schema_cache[org_id]


def get_schema_context_service(db: Session) -> SchemaContextService:
    """Factory function for SchemaContextService."""
    return SchemaContextService(db)
