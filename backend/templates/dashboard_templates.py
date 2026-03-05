"""
Dashboard Templates Registry.

Pre-built dashboard templates that auto-populate when data sources are connected.
Templates define metrics, charts, and required data sources.
"""
from typing import Dict, List, Any

# Widget types supported by the dashboard system
WIDGET_TYPES = ["big_number", "line_chart", "bar_chart", "pie_chart", "table"]

# Dashboard template categories
TEMPLATE_CATEGORIES = ["finance", "payments", "accounting", "banking", "operations"]

# Dashboard templates registry
DASHBOARD_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "revenue_overview": {
        "id": "revenue_overview",
        "name": "Revenue Overview",
        "description": "Track MRR, growth, churn, and top customers from your payment data",
        "category": "finance",
        "icon": "trending-up",
        "required_sources": ["stripe", "paystack"],  # OR condition - any of these
        "preview_image": "/images/dashboards/revenue-overview.png",
        "widgets": [
            {
                "id": "mrr",
                "type": "big_number",
                "title": "Monthly Recurring Revenue",
                "description": "Total MRR from active subscriptions",
                "position": {"x": 0, "y": 0, "w": 3, "h": 2},
                "config": {
                    "metric": "mrr",
                    "format": "currency",
                    "prefix": "",
                    "suffix": "/mo",
                    "trend_period": "month",
                },
                "sql_template": """
                    SELECT COALESCE(SUM(amount), 0) / 100.0 as value
                    FROM {source_table}_subscriptions
                    WHERE status = 'active'
                    AND current_period_end > NOW()
                """,
            },
            {
                "id": "growth_rate",
                "type": "big_number",
                "title": "Growth Rate",
                "description": "Month-over-month revenue growth",
                "position": {"x": 3, "y": 0, "w": 3, "h": 2},
                "config": {
                    "metric": "growth_rate",
                    "format": "percent",
                    "trend_period": "month",
                },
                "sql_template": """
                    WITH monthly_revenue AS (
                        SELECT
                            DATE_TRUNC('month', created_at) as month,
                            SUM(amount) / 100.0 as revenue
                        FROM {source_table}_payments
                        WHERE status = 'succeeded'
                        GROUP BY DATE_TRUNC('month', created_at)
                        ORDER BY month DESC
                        LIMIT 2
                    )
                    SELECT
                        CASE
                            WHEN LAG(revenue) OVER (ORDER BY month) > 0
                            THEN ((revenue - LAG(revenue) OVER (ORDER BY month)) / LAG(revenue) OVER (ORDER BY month)) * 100
                            ELSE 0
                        END as value
                    FROM monthly_revenue
                    ORDER BY month DESC
                    LIMIT 1
                """,
            },
            {
                "id": "churn_rate",
                "type": "big_number",
                "title": "Churn Rate",
                "description": "Percentage of churned subscriptions this month",
                "position": {"x": 6, "y": 0, "w": 3, "h": 2},
                "config": {
                    "metric": "churn_rate",
                    "format": "percent",
                    "color_thresholds": {"warning": 5, "danger": 10},
                },
                "sql_template": """
                    SELECT
                        CASE
                            WHEN COUNT(*) FILTER (WHERE status = 'active' OR canceled_at >= DATE_TRUNC('month', NOW())) > 0
                            THEN (COUNT(*) FILTER (WHERE canceled_at >= DATE_TRUNC('month', NOW())) * 100.0) /
                                 COUNT(*) FILTER (WHERE status = 'active' OR canceled_at >= DATE_TRUNC('month', NOW()))
                            ELSE 0
                        END as value
                    FROM {source_table}_subscriptions
                """,
            },
            {
                "id": "total_customers",
                "type": "big_number",
                "title": "Active Customers",
                "description": "Number of customers with active subscriptions",
                "position": {"x": 9, "y": 0, "w": 3, "h": 2},
                "config": {
                    "metric": "total_customers",
                    "format": "number",
                },
                "sql_template": """
                    SELECT COUNT(DISTINCT customer_id) as value
                    FROM {source_table}_subscriptions
                    WHERE status = 'active'
                """,
            },
            {
                "id": "revenue_trend",
                "type": "line_chart",
                "title": "Revenue Trend",
                "description": "Daily revenue over the last 30 days",
                "position": {"x": 0, "y": 2, "w": 8, "h": 4},
                "config": {
                    "x_axis": "date",
                    "y_axis": "revenue",
                    "format": "currency",
                },
                "sql_template": """
                    SELECT
                        DATE(created_at) as date,
                        SUM(amount) / 100.0 as revenue
                    FROM {source_table}_payments
                    WHERE status = 'succeeded'
                    AND created_at >= NOW() - INTERVAL '30 days'
                    GROUP BY DATE(created_at)
                    ORDER BY date
                """,
            },
            {
                "id": "top_customers",
                "type": "bar_chart",
                "title": "Top 10 Customers",
                "description": "Customers by total revenue",
                "position": {"x": 8, "y": 2, "w": 4, "h": 4},
                "config": {
                    "x_axis": "customer",
                    "y_axis": "revenue",
                    "format": "currency",
                    "orientation": "horizontal",
                },
                "sql_template": """
                    SELECT
                        COALESCE(c.email, c.name, 'Unknown') as customer,
                        SUM(p.amount) / 100.0 as revenue
                    FROM {source_table}_payments p
                    LEFT JOIN {source_table}_customers c ON p.customer_id = c.id
                    WHERE p.status = 'succeeded'
                    GROUP BY c.email, c.name
                    ORDER BY revenue DESC
                    LIMIT 10
                """,
            },
        ],
    },

    "cash_flow": {
        "id": "cash_flow",
        "name": "Cash Flow Dashboard",
        "description": "Monitor inflows, outflows, net cash flow and runway from accounting and banking data",
        "category": "finance",
        "icon": "wallet",
        "required_sources": ["xero", "quickbooks", "mono", "truelayer"],
        "preview_image": "/images/dashboards/cash-flow.png",
        "widgets": [
            {
                "id": "total_inflows",
                "type": "big_number",
                "title": "Total Inflows",
                "description": "Total cash inflows this month",
                "position": {"x": 0, "y": 0, "w": 3, "h": 2},
                "config": {
                    "metric": "total_inflows",
                    "format": "currency",
                    "color": "green",
                },
                "sql_template": """
                    SELECT COALESCE(SUM(amount), 0) as value
                    FROM {source_table}_transactions
                    WHERE type = 'credit'
                    AND date >= DATE_TRUNC('month', NOW())
                """,
            },
            {
                "id": "total_outflows",
                "type": "big_number",
                "title": "Total Outflows",
                "description": "Total cash outflows this month",
                "position": {"x": 3, "y": 0, "w": 3, "h": 2},
                "config": {
                    "metric": "total_outflows",
                    "format": "currency",
                    "color": "red",
                },
                "sql_template": """
                    SELECT COALESCE(SUM(ABS(amount)), 0) as value
                    FROM {source_table}_transactions
                    WHERE type = 'debit'
                    AND date >= DATE_TRUNC('month', NOW())
                """,
            },
            {
                "id": "net_cash_flow",
                "type": "big_number",
                "title": "Net Cash Flow",
                "description": "Net cash flow this month",
                "position": {"x": 6, "y": 0, "w": 3, "h": 2},
                "config": {
                    "metric": "net_cash_flow",
                    "format": "currency",
                },
                "sql_template": """
                    SELECT
                        COALESCE(SUM(CASE WHEN type = 'credit' THEN amount ELSE -ABS(amount) END), 0) as value
                    FROM {source_table}_transactions
                    WHERE date >= DATE_TRUNC('month', NOW())
                """,
            },
            {
                "id": "runway_estimate",
                "type": "big_number",
                "title": "Runway Estimate",
                "description": "Estimated months of runway based on burn rate",
                "position": {"x": 9, "y": 0, "w": 3, "h": 2},
                "config": {
                    "metric": "runway",
                    "format": "number",
                    "suffix": " months",
                    "color_thresholds": {"warning": 6, "danger": 3},
                },
                "sql_template": """
                    WITH current_balance AS (
                        SELECT COALESCE(SUM(CASE WHEN type = 'credit' THEN amount ELSE -ABS(amount) END), 0) as balance
                        FROM {source_table}_transactions
                    ),
                    monthly_burn AS (
                        SELECT COALESCE(AVG(monthly_outflow), 1) as avg_burn
                        FROM (
                            SELECT
                                DATE_TRUNC('month', date) as month,
                                SUM(ABS(amount)) as monthly_outflow
                            FROM {source_table}_transactions
                            WHERE type = 'debit'
                            AND date >= NOW() - INTERVAL '6 months'
                            GROUP BY DATE_TRUNC('month', date)
                        ) monthly
                    )
                    SELECT ROUND(cb.balance / NULLIF(mb.avg_burn, 0)) as value
                    FROM current_balance cb, monthly_burn mb
                """,
            },
            {
                "id": "cash_flow_trend",
                "type": "line_chart",
                "title": "Cash Flow Trend",
                "description": "Daily inflows and outflows over the last 30 days",
                "position": {"x": 0, "y": 2, "w": 12, "h": 4},
                "config": {
                    "x_axis": "date",
                    "y_axis": ["inflows", "outflows", "net"],
                    "format": "currency",
                    "colors": {"inflows": "#10b981", "outflows": "#ef4444", "net": "#3b82f6"},
                },
                "sql_template": """
                    SELECT
                        DATE(date) as date,
                        SUM(CASE WHEN type = 'credit' THEN amount ELSE 0 END) as inflows,
                        SUM(CASE WHEN type = 'debit' THEN ABS(amount) ELSE 0 END) as outflows,
                        SUM(CASE WHEN type = 'credit' THEN amount ELSE -ABS(amount) END) as net
                    FROM {source_table}_transactions
                    WHERE date >= NOW() - INTERVAL '30 days'
                    GROUP BY DATE(date)
                    ORDER BY date
                """,
            },
            {
                "id": "expense_breakdown",
                "type": "pie_chart",
                "title": "Expense Breakdown",
                "description": "Expenses by category",
                "position": {"x": 0, "y": 6, "w": 6, "h": 4},
                "config": {
                    "label": "category",
                    "value": "amount",
                    "format": "currency",
                },
                "sql_template": """
                    SELECT
                        COALESCE(category, 'Uncategorized') as category,
                        SUM(ABS(amount)) as amount
                    FROM {source_table}_transactions
                    WHERE type = 'debit'
                    AND date >= DATE_TRUNC('month', NOW())
                    GROUP BY category
                    ORDER BY amount DESC
                    LIMIT 8
                """,
            },
            {
                "id": "top_expenses",
                "type": "table",
                "title": "Top Expenses",
                "description": "Largest expenses this month",
                "position": {"x": 6, "y": 6, "w": 6, "h": 4},
                "config": {
                    "columns": ["description", "category", "amount", "date"],
                    "format": {"amount": "currency", "date": "date"},
                },
                "sql_template": """
                    SELECT
                        description,
                        COALESCE(category, 'Uncategorized') as category,
                        ABS(amount) as amount,
                        date
                    FROM {source_table}_transactions
                    WHERE type = 'debit'
                    AND date >= DATE_TRUNC('month', NOW())
                    ORDER BY ABS(amount) DESC
                    LIMIT 10
                """,
            },
        ],
    },

    "invoice_health": {
        "id": "invoice_health",
        "name": "Invoice Health",
        "description": "Track outstanding invoices, aging buckets, and collection performance",
        "category": "accounting",
        "icon": "file-text",
        "required_sources": ["xero", "quickbooks", "sage", "freeagent"],
        "preview_image": "/images/dashboards/invoice-health.png",
        "widgets": [
            {
                "id": "total_outstanding",
                "type": "big_number",
                "title": "Total Outstanding",
                "description": "Total value of unpaid invoices",
                "position": {"x": 0, "y": 0, "w": 3, "h": 2},
                "config": {
                    "metric": "total_outstanding",
                    "format": "currency",
                },
                "sql_template": """
                    SELECT COALESCE(SUM(amount_due - amount_paid), 0) as value
                    FROM {source_table}_invoices
                    WHERE status IN ('sent', 'partial', 'overdue')
                """,
            },
            {
                "id": "overdue_amount",
                "type": "big_number",
                "title": "Overdue Amount",
                "description": "Total overdue invoice value",
                "position": {"x": 3, "y": 0, "w": 3, "h": 2},
                "config": {
                    "metric": "overdue_amount",
                    "format": "currency",
                    "color": "red",
                },
                "sql_template": """
                    SELECT COALESCE(SUM(amount_due - amount_paid), 0) as value
                    FROM {source_table}_invoices
                    WHERE status IN ('sent', 'partial', 'overdue')
                    AND due_date < NOW()
                """,
            },
            {
                "id": "overdue_percent",
                "type": "big_number",
                "title": "Overdue %",
                "description": "Percentage of invoices that are overdue",
                "position": {"x": 6, "y": 0, "w": 3, "h": 2},
                "config": {
                    "metric": "overdue_percent",
                    "format": "percent",
                    "color_thresholds": {"warning": 10, "danger": 25},
                },
                "sql_template": """
                    SELECT
                        CASE
                            WHEN COUNT(*) > 0
                            THEN (COUNT(*) FILTER (WHERE due_date < NOW()) * 100.0) / COUNT(*)
                            ELSE 0
                        END as value
                    FROM {source_table}_invoices
                    WHERE status IN ('sent', 'partial', 'overdue')
                """,
            },
            {
                "id": "avg_days_to_pay",
                "type": "big_number",
                "title": "Avg Days to Pay",
                "description": "Average days to collect payment",
                "position": {"x": 9, "y": 0, "w": 3, "h": 2},
                "config": {
                    "metric": "avg_days_to_pay",
                    "format": "number",
                    "suffix": " days",
                },
                "sql_template": """
                    SELECT COALESCE(AVG(EXTRACT(DAY FROM (paid_at - issued_date))), 0)::integer as value
                    FROM {source_table}_invoices
                    WHERE status = 'paid'
                    AND paid_at IS NOT NULL
                    AND issued_date >= NOW() - INTERVAL '90 days'
                """,
            },
            {
                "id": "aging_buckets",
                "type": "bar_chart",
                "title": "Invoice Aging",
                "description": "Outstanding invoices by aging bucket",
                "position": {"x": 0, "y": 2, "w": 6, "h": 4},
                "config": {
                    "x_axis": "bucket",
                    "y_axis": "amount",
                    "format": "currency",
                    "colors": {
                        "Current": "#10b981",
                        "1-30 Days": "#f59e0b",
                        "31-60 Days": "#f97316",
                        "61-90 Days": "#ef4444",
                        "90+ Days": "#dc2626",
                    },
                },
                "sql_template": """
                    SELECT
                        CASE
                            WHEN due_date >= NOW() THEN 'Current'
                            WHEN NOW() - due_date <= INTERVAL '30 days' THEN '1-30 Days'
                            WHEN NOW() - due_date <= INTERVAL '60 days' THEN '31-60 Days'
                            WHEN NOW() - due_date <= INTERVAL '90 days' THEN '61-90 Days'
                            ELSE '90+ Days'
                        END as bucket,
                        SUM(amount_due - amount_paid) as amount
                    FROM {source_table}_invoices
                    WHERE status IN ('sent', 'partial', 'overdue')
                    GROUP BY bucket
                    ORDER BY
                        CASE bucket
                            WHEN 'Current' THEN 1
                            WHEN '1-30 Days' THEN 2
                            WHEN '31-60 Days' THEN 3
                            WHEN '61-90 Days' THEN 4
                            ELSE 5
                        END
                """,
            },
            {
                "id": "invoice_status_dist",
                "type": "pie_chart",
                "title": "Invoice Status",
                "description": "Distribution of invoice statuses",
                "position": {"x": 6, "y": 2, "w": 6, "h": 4},
                "config": {
                    "label": "status",
                    "value": "count",
                    "format": "number",
                },
                "sql_template": """
                    SELECT
                        INITCAP(status) as status,
                        COUNT(*) as count
                    FROM {source_table}_invoices
                    WHERE issued_date >= NOW() - INTERVAL '90 days'
                    GROUP BY status
                """,
            },
            {
                "id": "overdue_invoices",
                "type": "table",
                "title": "Overdue Invoices",
                "description": "List of overdue invoices sorted by amount",
                "position": {"x": 0, "y": 6, "w": 12, "h": 4},
                "config": {
                    "columns": ["customer", "invoice_number", "amount", "due_date", "days_overdue"],
                    "format": {"amount": "currency", "due_date": "date"},
                },
                "sql_template": """
                    SELECT
                        COALESCE(customer_name, customer_email, 'Unknown') as customer,
                        invoice_number,
                        (amount_due - amount_paid) as amount,
                        due_date,
                        EXTRACT(DAY FROM (NOW() - due_date))::integer as days_overdue
                    FROM {source_table}_invoices
                    WHERE status IN ('sent', 'partial', 'overdue')
                    AND due_date < NOW()
                    ORDER BY amount DESC
                    LIMIT 20
                """,
            },
        ],
    },

    "payment_analytics": {
        "id": "payment_analytics",
        "name": "Payment Analytics",
        "description": "Analyze payment success rates, failure reasons, refunds, and transaction volumes",
        "category": "payments",
        "icon": "credit-card",
        "required_sources": ["stripe", "paystack", "flutterwave", "gocardless"],
        "preview_image": "/images/dashboards/payment-analytics.png",
        "widgets": [
            {
                "id": "success_rate",
                "type": "big_number",
                "title": "Success Rate",
                "description": "Payment success rate (last 30 days)",
                "position": {"x": 0, "y": 0, "w": 3, "h": 2},
                "config": {
                    "metric": "success_rate",
                    "format": "percent",
                    "color_thresholds": {"warning": 95, "danger": 90},
                },
                "sql_template": """
                    SELECT
                        CASE
                            WHEN COUNT(*) > 0
                            THEN (COUNT(*) FILTER (WHERE status = 'succeeded') * 100.0) / COUNT(*)
                            ELSE 100
                        END as value
                    FROM {source_table}_payments
                    WHERE created_at >= NOW() - INTERVAL '30 days'
                """,
            },
            {
                "id": "total_volume",
                "type": "big_number",
                "title": "Total Volume",
                "description": "Total payment volume (last 30 days)",
                "position": {"x": 3, "y": 0, "w": 3, "h": 2},
                "config": {
                    "metric": "total_volume",
                    "format": "currency",
                },
                "sql_template": """
                    SELECT COALESCE(SUM(amount), 0) / 100.0 as value
                    FROM {source_table}_payments
                    WHERE status = 'succeeded'
                    AND created_at >= NOW() - INTERVAL '30 days'
                """,
            },
            {
                "id": "refund_rate",
                "type": "big_number",
                "title": "Refund Rate",
                "description": "Percentage of payments refunded",
                "position": {"x": 6, "y": 0, "w": 3, "h": 2},
                "config": {
                    "metric": "refund_rate",
                    "format": "percent",
                    "color_thresholds": {"warning": 2, "danger": 5},
                },
                "sql_template": """
                    SELECT
                        CASE
                            WHEN COUNT(*) FILTER (WHERE status = 'succeeded') > 0
                            THEN (SUM(CASE WHEN refunded THEN 1 ELSE 0 END) * 100.0) /
                                 COUNT(*) FILTER (WHERE status = 'succeeded')
                            ELSE 0
                        END as value
                    FROM {source_table}_payments
                    WHERE created_at >= NOW() - INTERVAL '30 days'
                """,
            },
            {
                "id": "avg_transaction",
                "type": "big_number",
                "title": "Avg Transaction",
                "description": "Average successful transaction value",
                "position": {"x": 9, "y": 0, "w": 3, "h": 2},
                "config": {
                    "metric": "avg_transaction",
                    "format": "currency",
                },
                "sql_template": """
                    SELECT COALESCE(AVG(amount), 0) / 100.0 as value
                    FROM {source_table}_payments
                    WHERE status = 'succeeded'
                    AND created_at >= NOW() - INTERVAL '30 days'
                """,
            },
            {
                "id": "payment_volume_trend",
                "type": "line_chart",
                "title": "Payment Volume Trend",
                "description": "Daily payment volume and count",
                "position": {"x": 0, "y": 2, "w": 8, "h": 4},
                "config": {
                    "x_axis": "date",
                    "y_axis": ["volume", "count"],
                    "format": {"volume": "currency", "count": "number"},
                },
                "sql_template": """
                    SELECT
                        DATE(created_at) as date,
                        SUM(amount) / 100.0 as volume,
                        COUNT(*) as count
                    FROM {source_table}_payments
                    WHERE status = 'succeeded'
                    AND created_at >= NOW() - INTERVAL '30 days'
                    GROUP BY DATE(created_at)
                    ORDER BY date
                """,
            },
            {
                "id": "failure_reasons",
                "type": "pie_chart",
                "title": "Failure Reasons",
                "description": "Distribution of payment failure reasons",
                "position": {"x": 8, "y": 2, "w": 4, "h": 4},
                "config": {
                    "label": "reason",
                    "value": "count",
                    "format": "number",
                },
                "sql_template": """
                    SELECT
                        COALESCE(failure_code, failure_message, 'Unknown') as reason,
                        COUNT(*) as count
                    FROM {source_table}_payments
                    WHERE status = 'failed'
                    AND created_at >= NOW() - INTERVAL '30 days'
                    GROUP BY reason
                    ORDER BY count DESC
                    LIMIT 6
                """,
            },
            {
                "id": "payment_methods",
                "type": "bar_chart",
                "title": "Payment Methods",
                "description": "Volume by payment method",
                "position": {"x": 0, "y": 6, "w": 6, "h": 4},
                "config": {
                    "x_axis": "method",
                    "y_axis": "volume",
                    "format": "currency",
                },
                "sql_template": """
                    SELECT
                        COALESCE(INITCAP(payment_method_type), 'Unknown') as method,
                        SUM(amount) / 100.0 as volume
                    FROM {source_table}_payments
                    WHERE status = 'succeeded'
                    AND created_at >= NOW() - INTERVAL '30 days'
                    GROUP BY payment_method_type
                    ORDER BY volume DESC
                """,
            },
            {
                "id": "recent_failures",
                "type": "table",
                "title": "Recent Failed Payments",
                "description": "Latest failed payment attempts",
                "position": {"x": 6, "y": 6, "w": 6, "h": 4},
                "config": {
                    "columns": ["customer", "amount", "reason", "created_at"],
                    "format": {"amount": "currency", "created_at": "datetime"},
                },
                "sql_template": """
                    SELECT
                        COALESCE(customer_email, 'Unknown') as customer,
                        amount / 100.0 as amount,
                        COALESCE(failure_code, failure_message, 'Unknown') as reason,
                        created_at
                    FROM {source_table}_payments
                    WHERE status = 'failed'
                    ORDER BY created_at DESC
                    LIMIT 10
                """,
            },
        ],
    },
}


def get_all_dashboard_templates() -> List[Dict[str, Any]]:
    """Get all available dashboard templates (summary view)."""
    return [
        {
            "id": t["id"],
            "name": t["name"],
            "description": t["description"],
            "category": t["category"],
            "icon": t["icon"],
            "required_sources": t["required_sources"],
            "preview_image": t.get("preview_image"),
            "widget_count": len(t["widgets"]),
        }
        for t in DASHBOARD_TEMPLATES.values()
    ]


def get_dashboard_template_by_id(template_id: str) -> Dict[str, Any] | None:
    """Get a dashboard template by ID with full details."""
    return DASHBOARD_TEMPLATES.get(template_id)


def get_templates_by_category(category: str) -> List[Dict[str, Any]]:
    """Get all templates in a specific category."""
    return [
        t for t in get_all_dashboard_templates()
        if t["category"] == category
    ]


def get_available_templates_for_sources(source_types: List[str]) -> List[Dict[str, Any]]:
    """Get templates that can be used with the given source types."""
    available = []
    source_types_lower = [s.lower() for s in source_types]

    for template in get_all_dashboard_templates():
        # Check if any required source is connected (OR condition)
        if any(req.lower() in source_types_lower for req in template["required_sources"]):
            template_copy = template.copy()
            template_copy["available"] = True
            available.append(template_copy)
        else:
            template_copy = template.copy()
            template_copy["available"] = False
            available.append(template_copy)

    return available


# ============================================================
# Industry-Specific Dashboard Templates
# ============================================================
# These are opinionated, pre-built dashboards tailored to common
# African/UK SME business types.  SQL templates use
# {transactions_table} / {orders_table} etc. as placeholders;
# DashboardService.create_dashboard_from_industry_template()
# resolves them against the org's actual destination schema.
#
# Widget types mirror WIDGET_TYPES above:
#   "kpi"        → single big number   (alias for "big_number")
#   "line_chart" → time-series line chart
#   "bar_chart"  → categorical bar chart
#   "pie_chart"  → proportion/donut
#   "table"      → tabular list
# ============================================================

INDUSTRY_DASHBOARD_TEMPLATES: Dict[str, Dict[str, Any]] = {
    # ----------------------------------------------------------
    # 1. E-commerce / Retail
    # ----------------------------------------------------------
    "ecommerce": {
        "id": "ecommerce",
        "name": "E-commerce & Retail",
        "description": (
            "Track sales, revenue, GMV, and customer behaviour for online "
            "and physical retail businesses."
        ),
        "icon": "shopping-bag",
        "industry": "ecommerce",
        "target_connectors": ["stripe", "paystack", "shopify", "woocommerce"],
        "recommended_for_source_types": ["stripe", "paystack", "shopify"],
        "widgets": [
            {
                "id": "total_revenue_30d",
                "type": "kpi",
                "title": "Total Revenue (Last 30 Days)",
                "description": "Gross revenue from all completed orders",
                "position": {"x": 0, "y": 0, "w": 3, "h": 2},
                "format": "currency",
                "currency": "auto",
                "sql_template": """
                    SELECT COALESCE(SUM(amount), 0) / 100.0 AS value
                    FROM {transactions_table}
                    WHERE status IN ('succeeded', 'completed', 'paid')
                      AND created_at >= NOW() - INTERVAL '30 days'
                """,
            },
            {
                "id": "order_count_30d",
                "type": "kpi",
                "title": "Orders This Month",
                "description": "Number of completed orders in the last 30 days",
                "position": {"x": 3, "y": 0, "w": 3, "h": 2},
                "format": "number",
                "sql_template": """
                    SELECT COUNT(*) AS value
                    FROM {orders_table}
                    WHERE status IN ('completed', 'delivered', 'paid')
                      AND created_at >= NOW() - INTERVAL '30 days'
                """,
            },
            {
                "id": "average_order_value",
                "type": "kpi",
                "title": "Average Order Value",
                "description": "Mean order amount over the last 30 days",
                "position": {"x": 6, "y": 0, "w": 3, "h": 2},
                "format": "currency",
                "currency": "auto",
                "sql_template": """
                    SELECT COALESCE(AVG(amount), 0) / 100.0 AS value
                    FROM {transactions_table}
                    WHERE status IN ('succeeded', 'completed', 'paid')
                      AND created_at >= NOW() - INTERVAL '30 days'
                """,
            },
            {
                "id": "revenue_trend",
                "type": "line_chart",
                "title": "Daily Revenue — Last 30 Days",
                "position": {"x": 0, "y": 2, "w": 8, "h": 4},
                "x_axis": "date",
                "y_axis": "revenue",
                "format": "currency",
                "sql_template": """
                    SELECT
                        DATE(created_at)                     AS date,
                        COALESCE(SUM(amount), 0) / 100.0     AS revenue
                    FROM {transactions_table}
                    WHERE status IN ('succeeded', 'completed', 'paid')
                      AND created_at >= NOW() - INTERVAL '30 days'
                    GROUP BY DATE(created_at)
                    ORDER BY date
                """,
            },
            {
                "id": "top_products",
                "type": "bar_chart",
                "title": "Top 10 Products by Revenue",
                "position": {"x": 0, "y": 6, "w": 6, "h": 4},
                "x_axis": "product_name",
                "y_axis": "revenue",
                "sql_template": """
                    SELECT
                        COALESCE(product_name, description, 'Unknown') AS product_name,
                        COALESCE(SUM(amount), 0) / 100.0               AS revenue
                    FROM {transactions_table}
                    WHERE status IN ('succeeded', 'completed', 'paid')
                    GROUP BY 1
                    ORDER BY revenue DESC
                    LIMIT 10
                """,
            },
            {
                "id": "payment_method_split",
                "type": "pie_chart",
                "title": "Payment Method Breakdown",
                "position": {"x": 6, "y": 6, "w": 6, "h": 4},
                "sql_template": """
                    SELECT
                        COALESCE(payment_method_type, payment_method, 'Other') AS method,
                        COUNT(*) AS count
                    FROM {transactions_table}
                    WHERE status IN ('succeeded', 'completed', 'paid')
                      AND created_at >= NOW() - INTERVAL '30 days'
                    GROUP BY 1
                    ORDER BY count DESC
                """,
            },
            {
                "id": "recent_orders",
                "type": "table",
                "title": "Recent Orders",
                "position": {"x": 0, "y": 10, "w": 12, "h": 4},
                "sql_template": """
                    SELECT
                        id                                       AS order_id,
                        COALESCE(customer_email, customer_id, 'Guest') AS customer,
                        COALESCE(amount, 0) / 100.0              AS amount,
                        status,
                        created_at
                    FROM {transactions_table}
                    ORDER BY created_at DESC
                    LIMIT 20
                """,
            },
        ],
    },

    # ----------------------------------------------------------
    # 2. Food & Beverage / Restaurant
    # ----------------------------------------------------------
    "food_beverage": {
        "id": "food_beverage",
        "name": "Food & Beverage (Restaurant)",
        "description": (
            "Monitor daily sales, peak trading hours, menu performance, "
            "and staff metrics for restaurants and food businesses."
        ),
        "icon": "utensils",
        "industry": "food_beverage",
        "target_connectors": ["stripe", "paystack", "square", "lightspeed"],
        "recommended_for_source_types": ["stripe", "paystack", "square"],
        "widgets": [
            {
                "id": "daily_revenue",
                "type": "kpi",
                "title": "Today's Revenue",
                "description": "Total sales taken today",
                "position": {"x": 0, "y": 0, "w": 3, "h": 2},
                "format": "currency",
                "currency": "auto",
                "sql_template": """
                    SELECT COALESCE(SUM(amount), 0) / 100.0 AS value
                    FROM {transactions_table}
                    WHERE status IN ('succeeded', 'completed', 'paid')
                      AND DATE(created_at) = CURRENT_DATE
                """,
            },
            {
                "id": "covers_today",
                "type": "kpi",
                "title": "Covers Today",
                "description": "Number of transactions (proxy for table covers) today",
                "position": {"x": 3, "y": 0, "w": 3, "h": 2},
                "format": "number",
                "sql_template": """
                    SELECT COUNT(*) AS value
                    FROM {transactions_table}
                    WHERE status IN ('succeeded', 'completed', 'paid')
                      AND DATE(created_at) = CURRENT_DATE
                """,
            },
            {
                "id": "avg_spend_per_cover",
                "type": "kpi",
                "title": "Avg Spend / Cover",
                "description": "Average transaction amount today",
                "position": {"x": 6, "y": 0, "w": 3, "h": 2},
                "format": "currency",
                "currency": "auto",
                "sql_template": """
                    SELECT COALESCE(AVG(amount), 0) / 100.0 AS value
                    FROM {transactions_table}
                    WHERE status IN ('succeeded', 'completed', 'paid')
                      AND DATE(created_at) = CURRENT_DATE
                """,
            },
            {
                "id": "weekly_revenue_trend",
                "type": "line_chart",
                "title": "Daily Revenue — Last 14 Days",
                "position": {"x": 0, "y": 2, "w": 8, "h": 4},
                "x_axis": "date",
                "y_axis": "revenue",
                "sql_template": """
                    SELECT
                        DATE(created_at)                     AS date,
                        COALESCE(SUM(amount), 0) / 100.0     AS revenue
                    FROM {transactions_table}
                    WHERE status IN ('succeeded', 'completed', 'paid')
                      AND created_at >= NOW() - INTERVAL '14 days'
                    GROUP BY DATE(created_at)
                    ORDER BY date
                """,
            },
            {
                "id": "peak_hours",
                "type": "bar_chart",
                "title": "Peak Trading Hours (Last 7 Days)",
                "position": {"x": 0, "y": 6, "w": 6, "h": 4},
                "x_axis": "hour_of_day",
                "y_axis": "transaction_count",
                "sql_template": """
                    SELECT
                        EXTRACT(HOUR FROM created_at)::int  AS hour_of_day,
                        COUNT(*)                             AS transaction_count,
                        COALESCE(SUM(amount), 0) / 100.0    AS revenue
                    FROM {transactions_table}
                    WHERE status IN ('succeeded', 'completed', 'paid')
                      AND created_at >= NOW() - INTERVAL '7 days'
                    GROUP BY 1
                    ORDER BY hour_of_day
                """,
            },
            {
                "id": "top_menu_items",
                "type": "bar_chart",
                "title": "Top 10 Menu Items by Revenue",
                "position": {"x": 6, "y": 6, "w": 6, "h": 4},
                "x_axis": "item_name",
                "y_axis": "revenue",
                "sql_template": """
                    SELECT
                        COALESCE(product_name, description, item_name, 'Unknown') AS item_name,
                        COALESCE(SUM(amount), 0) / 100.0                          AS revenue,
                        COUNT(*)                                                   AS quantity_sold
                    FROM {transactions_table}
                    WHERE status IN ('succeeded', 'completed', 'paid')
                      AND created_at >= NOW() - INTERVAL '30 days'
                    GROUP BY 1
                    ORDER BY revenue DESC
                    LIMIT 10
                """,
            },
            {
                "id": "day_of_week_performance",
                "type": "bar_chart",
                "title": "Revenue by Day of Week",
                "position": {"x": 0, "y": 10, "w": 12, "h": 4},
                "x_axis": "day_of_week",
                "y_axis": "revenue",
                "sql_template": """
                    SELECT
                        TO_CHAR(created_at, 'Day')           AS day_of_week,
                        EXTRACT(DOW FROM created_at)::int    AS day_num,
                        COALESCE(SUM(amount), 0) / 100.0     AS revenue,
                        COUNT(*)                             AS covers
                    FROM {transactions_table}
                    WHERE status IN ('succeeded', 'completed', 'paid')
                      AND created_at >= NOW() - INTERVAL '30 days'
                    GROUP BY 1, 2
                    ORDER BY day_num
                """,
            },
        ],
    },

    # ----------------------------------------------------------
    # 3. Fintech / Payments
    # ----------------------------------------------------------
    "fintech_payments": {
        "id": "fintech_payments",
        "name": "Fintech & Payments",
        "description": (
            "Monitor transaction volume, payment success rates, fraud rates, "
            "and daily float for payment-focused businesses."
        ),
        "icon": "credit-card",
        "industry": "fintech",
        "target_connectors": ["stripe", "paystack", "flutterwave", "mono"],
        "recommended_for_source_types": ["stripe", "paystack", "flutterwave"],
        "widgets": [
            {
                "id": "txn_volume_30d",
                "type": "kpi",
                "title": "Transaction Volume (30 Days)",
                "description": "Total value of all transactions processed",
                "position": {"x": 0, "y": 0, "w": 3, "h": 2},
                "format": "currency",
                "currency": "auto",
                "sql_template": """
                    SELECT COALESCE(SUM(amount), 0) / 100.0 AS value
                    FROM {transactions_table}
                    WHERE created_at >= NOW() - INTERVAL '30 days'
                """,
            },
            {
                "id": "success_rate",
                "type": "kpi",
                "title": "Payment Success Rate",
                "description": "Percentage of transactions that succeeded (last 30 days)",
                "position": {"x": 3, "y": 0, "w": 3, "h": 2},
                "format": "percent",
                "sql_template": """
                    SELECT
                        ROUND(
                            100.0 * SUM(CASE WHEN status IN ('succeeded','paid','completed') THEN 1 ELSE 0 END)
                            / NULLIF(COUNT(*), 0),
                        2) AS value
                    FROM {transactions_table}
                    WHERE created_at >= NOW() - INTERVAL '30 days'
                """,
            },
            {
                "id": "failed_txn_count",
                "type": "kpi",
                "title": "Failed Transactions (30 Days)",
                "description": "Count of failed/declined transactions",
                "position": {"x": 6, "y": 0, "w": 3, "h": 2},
                "format": "number",
                "sql_template": """
                    SELECT COUNT(*) AS value
                    FROM {transactions_table}
                    WHERE status IN ('failed', 'declined', 'error', 'cancelled')
                      AND created_at >= NOW() - INTERVAL '30 days'
                """,
            },
            {
                "id": "daily_volume_trend",
                "type": "line_chart",
                "title": "Daily Transaction Volume — Last 30 Days",
                "position": {"x": 0, "y": 2, "w": 8, "h": 4},
                "x_axis": "date",
                "y_axis": "volume",
                "sql_template": """
                    SELECT
                        DATE(created_at)                     AS date,
                        COALESCE(SUM(amount), 0) / 100.0     AS volume,
                        COUNT(*)                             AS transaction_count
                    FROM {transactions_table}
                    WHERE created_at >= NOW() - INTERVAL '30 days'
                    GROUP BY DATE(created_at)
                    ORDER BY date
                """,
            },
            {
                "id": "failure_reasons",
                "type": "bar_chart",
                "title": "Top Failure Reasons",
                "position": {"x": 0, "y": 6, "w": 6, "h": 4},
                "x_axis": "failure_reason",
                "y_axis": "count",
                "sql_template": """
                    SELECT
                        COALESCE(failure_code, failure_message, decline_code, 'Unknown') AS failure_reason,
                        COUNT(*) AS count
                    FROM {transactions_table}
                    WHERE status IN ('failed', 'declined', 'error')
                      AND created_at >= NOW() - INTERVAL '30 days'
                    GROUP BY 1
                    ORDER BY count DESC
                    LIMIT 10
                """,
            },
            {
                "id": "currency_breakdown",
                "type": "pie_chart",
                "title": "Volume by Currency",
                "position": {"x": 6, "y": 6, "w": 6, "h": 4},
                "sql_template": """
                    SELECT
                        UPPER(COALESCE(currency, 'UNKNOWN')) AS currency,
                        COALESCE(SUM(amount), 0) / 100.0     AS volume
                    FROM {transactions_table}
                    WHERE status IN ('succeeded', 'paid', 'completed')
                      AND created_at >= NOW() - INTERVAL '30 days'
                    GROUP BY 1
                    ORDER BY volume DESC
                """,
            },
            {
                "id": "daily_float",
                "type": "table",
                "title": "Daily Float Summary (Last 7 Days)",
                "position": {"x": 0, "y": 10, "w": 12, "h": 4},
                "sql_template": """
                    SELECT
                        DATE(created_at)                                                       AS date,
                        COUNT(*)                                                               AS total_transactions,
                        SUM(CASE WHEN status IN ('succeeded','paid','completed') THEN 1 ELSE 0 END) AS successful,
                        SUM(CASE WHEN status IN ('failed','declined','error')    THEN 1 ELSE 0 END) AS failed,
                        COALESCE(SUM(CASE WHEN status IN ('succeeded','paid','completed')
                            THEN amount ELSE 0 END), 0) / 100.0                               AS net_volume
                    FROM {transactions_table}
                    WHERE created_at >= NOW() - INTERVAL '7 days'
                    GROUP BY DATE(created_at)
                    ORDER BY date DESC
                """,
            },
        ],
    },

    # ----------------------------------------------------------
    # 4. Professional Services (Agency / Consulting)
    # ----------------------------------------------------------
    "professional_services": {
        "id": "professional_services",
        "name": "Professional Services",
        "description": (
            "Track project revenue, client billing, team utilisation, "
            "and invoice ageing for agencies and consulting firms."
        ),
        "icon": "briefcase",
        "industry": "professional_services",
        "target_connectors": ["xero", "quickbooks", "freeagent", "sage", "stripe"],
        "recommended_for_source_types": ["xero", "quickbooks", "freeagent", "sage"],
        "widgets": [
            {
                "id": "revenue_30d",
                "type": "kpi",
                "title": "Revenue (Last 30 Days)",
                "description": "Total invoiced / billed amount in the period",
                "position": {"x": 0, "y": 0, "w": 3, "h": 2},
                "format": "currency",
                "currency": "auto",
                "sql_template": """
                    SELECT COALESCE(SUM(total_amount), 0) AS value
                    FROM {invoices_table}
                    WHERE status IN ('paid', 'authorised', 'approved')
                      AND invoice_date >= NOW() - INTERVAL '30 days'
                """,
            },
            {
                "id": "outstanding_invoices",
                "type": "kpi",
                "title": "Outstanding Invoices",
                "description": "Total value of unpaid invoices",
                "position": {"x": 3, "y": 0, "w": 3, "h": 2},
                "format": "currency",
                "currency": "auto",
                "sql_template": """
                    SELECT COALESCE(SUM(amount_due), SUM(total_amount), 0) AS value
                    FROM {invoices_table}
                    WHERE status IN ('sent', 'overdue', 'draft', 'submitted')
                """,
            },
            {
                "id": "overdue_count",
                "type": "kpi",
                "title": "Overdue Invoices",
                "description": "Number of invoices past their due date",
                "position": {"x": 6, "y": 0, "w": 3, "h": 2},
                "format": "number",
                "sql_template": """
                    SELECT COUNT(*) AS value
                    FROM {invoices_table}
                    WHERE status NOT IN ('paid', 'voided', 'cancelled')
                      AND due_date < CURRENT_DATE
                """,
            },
            {
                "id": "monthly_revenue_trend",
                "type": "line_chart",
                "title": "Monthly Revenue Trend",
                "position": {"x": 0, "y": 2, "w": 8, "h": 4},
                "x_axis": "month",
                "y_axis": "revenue",
                "sql_template": """
                    SELECT
                        DATE_TRUNC('month', invoice_date)    AS month,
                        COALESCE(SUM(total_amount), 0)       AS revenue,
                        COUNT(*)                             AS invoice_count
                    FROM {invoices_table}
                    WHERE status IN ('paid', 'authorised', 'approved')
                      AND invoice_date >= NOW() - INTERVAL '12 months'
                    GROUP BY DATE_TRUNC('month', invoice_date)
                    ORDER BY month
                """,
            },
            {
                "id": "top_clients",
                "type": "bar_chart",
                "title": "Top 10 Clients by Revenue",
                "position": {"x": 0, "y": 6, "w": 6, "h": 4},
                "x_axis": "client_name",
                "y_axis": "revenue",
                "sql_template": """
                    SELECT
                        COALESCE(contact_name, client_name, customer_name, 'Unknown') AS client_name,
                        COALESCE(SUM(total_amount), 0)                                AS revenue,
                        COUNT(*)                                                       AS invoice_count
                    FROM {invoices_table}
                    WHERE status IN ('paid', 'authorised', 'approved')
                    GROUP BY 1
                    ORDER BY revenue DESC
                    LIMIT 10
                """,
            },
            {
                "id": "invoice_aging",
                "type": "bar_chart",
                "title": "Invoice Ageing (Unpaid)",
                "position": {"x": 6, "y": 6, "w": 6, "h": 4},
                "x_axis": "aging_bucket",
                "y_axis": "amount",
                "sql_template": """
                    SELECT
                        CASE
                            WHEN due_date >= CURRENT_DATE                              THEN 'Current'
                            WHEN due_date >= CURRENT_DATE - INTERVAL '30 days'         THEN '1-30 days'
                            WHEN due_date >= CURRENT_DATE - INTERVAL '60 days'         THEN '31-60 days'
                            WHEN due_date >= CURRENT_DATE - INTERVAL '90 days'         THEN '61-90 days'
                            ELSE '90+ days'
                        END                                                             AS aging_bucket,
                        COALESCE(SUM(COALESCE(amount_due, total_amount)), 0)            AS amount,
                        COUNT(*)                                                         AS invoice_count
                    FROM {invoices_table}
                    WHERE status NOT IN ('paid', 'voided', 'cancelled')
                    GROUP BY 1
                    ORDER BY
                        CASE aging_bucket
                            WHEN 'Current'    THEN 1
                            WHEN '1-30 days'  THEN 2
                            WHEN '31-60 days' THEN 3
                            WHEN '61-90 days' THEN 4
                            ELSE 5
                        END
                """,
            },
            {
                "id": "unpaid_invoices_list",
                "type": "table",
                "title": "Unpaid Invoices",
                "position": {"x": 0, "y": 10, "w": 12, "h": 4},
                "sql_template": """
                    SELECT
                        invoice_number,
                        COALESCE(contact_name, client_name, customer_name, 'Unknown') AS client,
                        COALESCE(total_amount, 0)                                      AS amount,
                        due_date,
                        status,
                        CURRENT_DATE - due_date                                        AS days_overdue
                    FROM {invoices_table}
                    WHERE status NOT IN ('paid', 'voided', 'cancelled')
                    ORDER BY due_date ASC
                    LIMIT 25
                """,
            },
        ],
    },

    # ----------------------------------------------------------
    # 5. SaaS / Tech Startup
    # ----------------------------------------------------------
    "saas_startup": {
        "id": "saas_startup",
        "name": "SaaS & Tech Startup",
        "description": (
            "Track MRR, churn, trial conversions, new signups, and revenue "
            "expansion for software-as-a-service businesses."
        ),
        "icon": "code",
        "industry": "saas",
        "target_connectors": ["stripe", "paystack"],
        "recommended_for_source_types": ["stripe", "paystack"],
        "widgets": [
            {
                "id": "mrr",
                "type": "kpi",
                "title": "Monthly Recurring Revenue",
                "description": "Current MRR from active subscriptions",
                "position": {"x": 0, "y": 0, "w": 3, "h": 2},
                "format": "currency",
                "currency": "auto",
                "sql_template": """
                    SELECT COALESCE(SUM(amount), 0) / 100.0 AS value
                    FROM {subscriptions_table}
                    WHERE status = 'active'
                      AND billing_interval IN ('month', 'monthly')
                """,
            },
            {
                "id": "active_subscriptions",
                "type": "kpi",
                "title": "Active Subscriptions",
                "description": "Total number of currently active paying subscribers",
                "position": {"x": 3, "y": 0, "w": 3, "h": 2},
                "format": "number",
                "sql_template": """
                    SELECT COUNT(*) AS value
                    FROM {subscriptions_table}
                    WHERE status = 'active'
                """,
            },
            {
                "id": "churn_rate",
                "type": "kpi",
                "title": "Monthly Churn Rate",
                "description": "Percentage of subscribers who cancelled last month",
                "position": {"x": 6, "y": 0, "w": 3, "h": 2},
                "format": "percent",
                "sql_template": """
                    WITH prev_month AS (
                        SELECT COUNT(*) AS active_count
                        FROM {subscriptions_table}
                        WHERE status = 'active'
                          AND created_at < DATE_TRUNC('month', CURRENT_DATE)
                    ),
                    churned AS (
                        SELECT COUNT(*) AS churned_count
                        FROM {subscriptions_table}
                        WHERE status IN ('canceled', 'cancelled', 'expired')
                          AND canceled_at >= DATE_TRUNC('month', NOW()) - INTERVAL '1 month'
                          AND canceled_at <  DATE_TRUNC('month', NOW())
                    )
                    SELECT
                        ROUND(
                            100.0 * churned.churned_count / NULLIF(prev_month.active_count, 0),
                        2) AS value
                    FROM prev_month, churned
                """,
            },
            {
                "id": "mrr_growth_trend",
                "type": "line_chart",
                "title": "MRR Growth — Last 12 Months",
                "position": {"x": 0, "y": 2, "w": 8, "h": 4},
                "x_axis": "month",
                "y_axis": "mrr",
                "sql_template": """
                    SELECT
                        DATE_TRUNC('month', created_at)      AS month,
                        COALESCE(SUM(amount), 0) / 100.0     AS mrr,
                        COUNT(*)                             AS new_subscriptions
                    FROM {subscriptions_table}
                    WHERE status IN ('active', 'canceled', 'cancelled')
                      AND created_at >= NOW() - INTERVAL '12 months'
                    GROUP BY DATE_TRUNC('month', created_at)
                    ORDER BY month
                """,
            },
            {
                "id": "plan_distribution",
                "type": "pie_chart",
                "title": "Subscribers by Plan",
                "position": {"x": 0, "y": 6, "w": 5, "h": 4},
                "sql_template": """
                    SELECT
                        COALESCE(plan_id, plan_name, price_id, 'Unknown') AS plan,
                        COUNT(*) AS subscriber_count
                    FROM {subscriptions_table}
                    WHERE status = 'active'
                    GROUP BY 1
                    ORDER BY subscriber_count DESC
                """,
            },
            {
                "id": "new_trials",
                "type": "bar_chart",
                "title": "New Trials Started (Daily — Last 30 Days)",
                "position": {"x": 5, "y": 6, "w": 7, "h": 4},
                "x_axis": "date",
                "y_axis": "trials",
                "sql_template": """
                    SELECT
                        DATE(created_at) AS date,
                        COUNT(*)         AS trials
                    FROM {subscriptions_table}
                    WHERE status IN ('trialing', 'trial')
                      AND created_at >= NOW() - INTERVAL '30 days'
                    GROUP BY DATE(created_at)
                    ORDER BY date
                """,
            },
            {
                "id": "recent_cancellations",
                "type": "table",
                "title": "Recent Cancellations",
                "position": {"x": 0, "y": 10, "w": 12, "h": 4},
                "sql_template": """
                    SELECT
                        id                                                         AS subscription_id,
                        COALESCE(customer_email, customer_id, 'Unknown')           AS customer,
                        COALESCE(plan_id, plan_name, price_id, 'Unknown')          AS plan,
                        canceled_at,
                        COALESCE(cancellation_reason, cancel_at_period_end::text, '') AS reason
                    FROM {subscriptions_table}
                    WHERE status IN ('canceled', 'cancelled', 'expired')
                      AND canceled_at >= NOW() - INTERVAL '30 days'
                    ORDER BY canceled_at DESC
                    LIMIT 20
                """,
            },
        ],
    },
}


# ---------------------------------------------------------------------------
# Helper functions for industry templates
# ---------------------------------------------------------------------------

def get_all_industry_templates() -> List[Dict[str, Any]]:
    """
    Return a summary list of all industry-specific dashboard templates.

    Each item contains metadata but not the full widget definitions.
    """
    return [
        {
            "id": t["id"],
            "name": t["name"],
            "description": t["description"],
            "icon": t["icon"],
            "industry": t["industry"],
            "target_connectors": t["target_connectors"],
            "recommended_for_source_types": t["recommended_for_source_types"],
            "widget_count": len(t["widgets"]),
        }
        for t in INDUSTRY_DASHBOARD_TEMPLATES.values()
    ]


def get_industry_template_by_id(template_id: str) -> Dict[str, Any]:
    """Return the full industry template dict (including widgets) or None."""
    return INDUSTRY_DASHBOARD_TEMPLATES.get(template_id)


def recommend_industry_template(source_types: List[str]) -> Any:
    """
    Given a list of connected source types, return the ID of the most
    relevant industry dashboard template.

    Scoring: count how many of the template's recommended_for_source_types
    match the org's connected sources; return the highest-scoring template ID.
    Returns None if no sources are connected.
    """
    if not source_types:
        return None

    source_set = {s.lower() for s in source_types}
    best_id = None
    best_score: int = -1

    for tmpl_id, tmpl in INDUSTRY_DASHBOARD_TEMPLATES.items():
        recommended = {s.lower() for s in tmpl.get("recommended_for_source_types", [])}
        score = len(recommended & source_set)
        if score > best_score:
            best_score = score
            best_id = tmpl_id

    return best_id if best_score > 0 else None
