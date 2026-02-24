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
