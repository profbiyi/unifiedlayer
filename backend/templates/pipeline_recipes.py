"""
Pipeline Recipes Registry.

Pre-configured pipeline templates for common business use cases.
"""
from typing import Dict, List, Any

# Recipe category types
RECIPE_CATEGORIES = {
    "finance": {
        "name": "Finance",
        "description": "Payment processing and revenue tracking",
        "icon": "wallet",
    },
    "accounting": {
        "name": "Accounting",
        "description": "Bookkeeping and financial records",
        "icon": "calculator",
    },
    "banking": {
        "name": "Banking",
        "description": "Bank transactions and account syncing",
        "icon": "building-columns",
    },
    "operations": {
        "name": "Operations",
        "description": "Database replication and data syncing",
        "icon": "database",
    },
}

# Pipeline recipes registry
PIPELINE_RECIPES: Dict[str, Dict[str, Any]] = {
    # ========================
    # FINANCE RECIPES
    # ========================
    "stripe_revenue_sync": {
        "name": "Sync Stripe Revenue",
        "description": "Daily sync of Stripe payments with MRR calculation and customer analytics",
        "category": "finance",
        "source_type": "stripe",
        "destination_type": None,  # Any destination
        "icon": "credit-card",
        "schedule": "0 6 * * *",  # 6am daily
        "schedule_description": "Daily at 6:00 AM",
        "tables": ["payments", "customers", "subscriptions", "invoices", "refunds"],
        "transformations": [
            {
                "name": "Calculate MRR",
                "description": "Calculate Monthly Recurring Revenue from active subscriptions",
                "sql": """
SELECT
    date_trunc('month', created_at) as month,
    COUNT(DISTINCT customer_id) as active_customers,
    SUM(amount) / 100.0 as mrr,
    SUM(CASE WHEN status = 'succeeded' THEN amount ELSE 0 END) / 100.0 as successful_revenue
FROM stripe_payments
WHERE status IN ('succeeded', 'pending')
GROUP BY 1
ORDER BY 1 DESC
""",
                "target_table": "stripe_mrr_summary",
                "execution_order": 1,
            },
            {
                "name": "Customer Lifetime Value",
                "description": "Calculate customer LTV based on payment history",
                "sql": """
SELECT
    customer_id,
    MIN(created_at) as first_payment_date,
    MAX(created_at) as last_payment_date,
    COUNT(*) as total_payments,
    SUM(amount) / 100.0 as lifetime_value,
    AVG(amount) / 100.0 as avg_payment_value
FROM stripe_payments
WHERE status = 'succeeded'
GROUP BY customer_id
""",
                "target_table": "stripe_customer_ltv",
                "execution_order": 2,
            },
        ],
        "estimated_rows_per_day": 1000,
        "use_cases": [
            "Track monthly recurring revenue",
            "Monitor customer churn",
            "Analyze payment trends",
            "Calculate customer lifetime value",
        ],
    },
    "paystack_transactions": {
        "name": "Track Paystack Transactions",
        "description": "Real-time Paystack transaction sync with categorization for African markets",
        "category": "finance",
        "source_type": "paystack",
        "destination_type": None,
        "icon": "naira-sign",
        "schedule": "*/30 * * * *",  # Every 30 minutes
        "schedule_description": "Every 30 minutes",
        "tables": ["transactions", "customers", "transfers", "settlements", "disputes"],
        "transformations": [
            {
                "name": "Daily Transaction Summary",
                "description": "Aggregate daily transaction volumes by currency",
                "sql": """
SELECT
    DATE(created_at) as transaction_date,
    currency,
    COUNT(*) as transaction_count,
    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful_count,
    SUM(CASE WHEN status = 'success' THEN amount ELSE 0 END) / 100.0 as total_successful_amount,
    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_count,
    AVG(CASE WHEN status = 'success' THEN amount ELSE NULL END) / 100.0 as avg_transaction_value
FROM paystack_transactions
GROUP BY DATE(created_at), currency
ORDER BY transaction_date DESC
""",
                "target_table": "paystack_daily_summary",
                "execution_order": 1,
            },
            {
                "name": "Settlement Reconciliation",
                "description": "Match transactions with settlements",
                "sql": """
SELECT
    s.id as settlement_id,
    s.settled_date,
    s.total_amount / 100.0 as settlement_amount,
    COUNT(t.id) as transaction_count,
    SUM(t.amount) / 100.0 as total_transactions,
    (s.total_amount - COALESCE(SUM(t.amount), 0)) / 100.0 as variance
FROM paystack_settlements s
LEFT JOIN paystack_transactions t ON t.settlement_id = s.id
GROUP BY s.id, s.settled_date, s.total_amount
""",
                "target_table": "paystack_settlement_reconciliation",
                "execution_order": 2,
            },
        ],
        "estimated_rows_per_day": 5000,
        "use_cases": [
            "Track payment success rates",
            "Monitor settlement timing",
            "Analyze transaction patterns",
            "Currency-based reporting for NGN, KES, GHS",
        ],
    },

    # ========================
    # ACCOUNTING RECIPES
    # ========================
    "quickbooks_full_sync": {
        "name": "QuickBooks Full Sync",
        "description": "Complete QuickBooks Online sync with P&L and balance sheet preparation",
        "category": "accounting",
        "source_type": "quickbooks",
        "destination_type": None,
        "icon": "file-invoice-dollar",
        "schedule": "0 1 * * *",  # 1am daily
        "schedule_description": "Daily at 1:00 AM",
        "tables": ["invoices", "bills", "accounts", "journal_entries", "customers", "vendors", "items"],
        "transformations": [
            {
                "name": "Accounts Receivable Aging",
                "description": "Calculate AR aging buckets",
                "sql": """
SELECT
    customer_id,
    customer_name,
    SUM(CASE WHEN days_outstanding <= 30 THEN balance_due ELSE 0 END) as current_30,
    SUM(CASE WHEN days_outstanding > 30 AND days_outstanding <= 60 THEN balance_due ELSE 0 END) as days_31_60,
    SUM(CASE WHEN days_outstanding > 60 AND days_outstanding <= 90 THEN balance_due ELSE 0 END) as days_61_90,
    SUM(CASE WHEN days_outstanding > 90 THEN balance_due ELSE 0 END) as over_90,
    SUM(balance_due) as total_outstanding
FROM (
    SELECT
        i.customer_id,
        c.display_name as customer_name,
        i.balance_due,
        EXTRACT(DAY FROM CURRENT_DATE - i.due_date) as days_outstanding
    FROM qb_invoices i
    JOIN qb_customers c ON i.customer_id = c.id
    WHERE i.balance_due > 0
) aging
GROUP BY customer_id, customer_name
ORDER BY total_outstanding DESC
""",
                "target_table": "qb_ar_aging",
                "execution_order": 1,
            },
            {
                "name": "Revenue by Category",
                "description": "Monthly revenue breakdown by product/service category",
                "sql": """
SELECT
    date_trunc('month', i.txn_date) as month,
    il.item_name,
    il.item_type,
    COUNT(DISTINCT i.id) as invoice_count,
    SUM(il.amount) as total_revenue,
    AVG(il.amount) as avg_line_amount
FROM qb_invoices i
JOIN qb_invoice_lines il ON i.id = il.invoice_id
WHERE i.txn_date >= CURRENT_DATE - INTERVAL '12 months'
GROUP BY date_trunc('month', i.txn_date), il.item_name, il.item_type
ORDER BY month DESC, total_revenue DESC
""",
                "target_table": "qb_revenue_by_category",
                "execution_order": 2,
            },
        ],
        "estimated_rows_per_day": 2000,
        "use_cases": [
            "Automate AR aging reports",
            "Track revenue by product/service",
            "Prepare for month-end close",
            "Monitor cash flow patterns",
        ],
    },
    "xero_accounting_sync": {
        "name": "Xero Accounting Sync",
        "description": "Full Xero accounting sync with UK VAT and MTD preparation",
        "category": "accounting",
        "source_type": "xero",
        "destination_type": None,
        "icon": "sterling-sign",
        "schedule": "0 2 * * *",  # 2am daily
        "schedule_description": "Daily at 2:00 AM",
        "tables": ["invoices", "bills", "bank_transactions", "accounts", "contacts", "manual_journals"],
        "transformations": [
            {
                "name": "VAT Summary",
                "description": "Calculate VAT liability for MTD submissions",
                "sql": """
SELECT
    date_trunc('quarter', txn_date) as vat_period,
    SUM(CASE WHEN type = 'ACCREC' THEN total_tax ELSE 0 END) as output_vat,
    SUM(CASE WHEN type = 'ACCPAY' THEN total_tax ELSE 0 END) as input_vat,
    SUM(CASE WHEN type = 'ACCREC' THEN total_tax ELSE 0 END) -
    SUM(CASE WHEN type = 'ACCPAY' THEN total_tax ELSE 0 END) as vat_liability,
    SUM(CASE WHEN type = 'ACCREC' THEN sub_total ELSE 0 END) as total_sales_ex_vat,
    SUM(CASE WHEN type = 'ACCPAY' THEN sub_total ELSE 0 END) as total_purchases_ex_vat
FROM xero_invoices
WHERE txn_date >= date_trunc('quarter', CURRENT_DATE - INTERVAL '3 months')
GROUP BY date_trunc('quarter', txn_date)
ORDER BY vat_period DESC
""",
                "target_table": "xero_vat_summary",
                "execution_order": 1,
            },
            {
                "name": "Profit & Loss Summary",
                "description": "Monthly P&L by account category",
                "sql": """
SELECT
    date_trunc('month', txn_date) as month,
    account_type,
    account_name,
    SUM(CASE WHEN is_credit THEN amount ELSE -amount END) as net_amount
FROM xero_journal_lines jl
JOIN xero_accounts a ON jl.account_id = a.id
WHERE txn_date >= CURRENT_DATE - INTERVAL '12 months'
GROUP BY date_trunc('month', txn_date), account_type, account_name
ORDER BY month DESC, account_type
""",
                "target_table": "xero_monthly_pl",
                "execution_order": 2,
            },
        ],
        "estimated_rows_per_day": 1500,
        "use_cases": [
            "Prepare VAT returns for HMRC MTD",
            "Generate P&L reports",
            "Track expenses by category",
            "Monitor cash position",
        ],
    },

    # ========================
    # BANKING RECIPES
    # ========================
    "mono_bank_sync": {
        "name": "Bank Transaction Sync (Mono)",
        "description": "Sync Nigerian bank transactions with auto-categorization",
        "category": "banking",
        "source_type": "mono",
        "destination_type": None,
        "icon": "building-columns",
        "schedule": "0 */4 * * *",  # Every 4 hours
        "schedule_description": "Every 4 hours",
        "tables": ["transactions", "accounts", "balances"],
        "transformations": [
            {
                "name": "Transaction Categorization",
                "description": "Auto-categorize transactions based on narration patterns",
                "sql": """
SELECT
    id,
    date,
    narration,
    amount,
    type,
    CASE
        WHEN LOWER(narration) LIKE '%salary%' OR LOWER(narration) LIKE '%payroll%' THEN 'Salary'
        WHEN LOWER(narration) LIKE '%transfer%' THEN 'Transfers'
        WHEN LOWER(narration) LIKE '%airtime%' OR LOWER(narration) LIKE '%mtn%' OR LOWER(narration) LIKE '%glo%' THEN 'Utilities'
        WHEN LOWER(narration) LIKE '%pos%' OR LOWER(narration) LIKE '%card%' THEN 'Card Transactions'
        WHEN LOWER(narration) LIKE '%loan%' OR LOWER(narration) LIKE '%repayment%' THEN 'Loans'
        WHEN LOWER(narration) LIKE '%atm%' OR LOWER(narration) LIKE '%withdrawal%' THEN 'Cash Withdrawals'
        ELSE 'Other'
    END as category,
    account_id
FROM mono_transactions
""",
                "target_table": "mono_categorized_transactions",
                "execution_order": 1,
            },
            {
                "name": "Daily Cash Flow",
                "description": "Daily cash inflows and outflows summary",
                "sql": """
SELECT
    DATE(date) as transaction_date,
    account_id,
    SUM(CASE WHEN type = 'credit' THEN amount ELSE 0 END) as total_inflows,
    SUM(CASE WHEN type = 'debit' THEN amount ELSE 0 END) as total_outflows,
    SUM(CASE WHEN type = 'credit' THEN amount ELSE -amount END) as net_flow,
    COUNT(*) as transaction_count
FROM mono_transactions
GROUP BY DATE(date), account_id
ORDER BY transaction_date DESC
""",
                "target_table": "mono_daily_cashflow",
                "execution_order": 2,
            },
        ],
        "estimated_rows_per_day": 200,
        "use_cases": [
            "Auto-categorize bank transactions",
            "Track daily cash flow",
            "Reconcile bank accounts",
            "Detect unusual transactions",
        ],
    },
    "truelayer_uk_banking": {
        "name": "UK Bank Sync (TrueLayer)",
        "description": "UK Open Banking transaction sync with spending analysis",
        "category": "banking",
        "source_type": "open_banking",
        "destination_type": None,
        "icon": "landmark",
        "schedule": "0 */6 * * *",  # Every 6 hours
        "schedule_description": "Every 6 hours",
        "tables": ["transactions", "accounts", "balances", "standing_orders", "direct_debits"],
        "transformations": [
            {
                "name": "Spending by Merchant Category",
                "description": "Categorize spending by merchant type",
                "sql": """
SELECT
    date_trunc('month', transaction_date) as month,
    merchant_category_code,
    merchant_category_name,
    COUNT(*) as transaction_count,
    SUM(amount) as total_spent,
    AVG(amount) as avg_transaction
FROM truelayer_transactions
WHERE amount < 0  -- Spending (negative amounts)
GROUP BY date_trunc('month', transaction_date), merchant_category_code, merchant_category_name
ORDER BY month DESC, total_spent
""",
                "target_table": "truelayer_spending_by_category",
                "execution_order": 1,
            },
            {
                "name": "Account Balance History",
                "description": "Track account balances over time",
                "sql": """
SELECT
    DATE(timestamp) as balance_date,
    account_id,
    account_name,
    currency,
    AVG(available_balance) as avg_balance,
    MIN(available_balance) as min_balance,
    MAX(available_balance) as max_balance
FROM truelayer_balances
GROUP BY DATE(timestamp), account_id, account_name, currency
ORDER BY balance_date DESC
""",
                "target_table": "truelayer_balance_history",
                "execution_order": 2,
            },
        ],
        "estimated_rows_per_day": 100,
        "use_cases": [
            "Track spending patterns",
            "Monitor account balances",
            "Identify recurring payments",
            "Expense categorization",
        ],
    },

    # ========================
    # OPERATIONS RECIPES
    # ========================
    "postgres_replication": {
        "name": "Database Replication (PostgreSQL)",
        "description": "Mirror production PostgreSQL tables to your data warehouse",
        "category": "operations",
        "source_type": "postgres",
        "destination_type": None,
        "icon": "database",
        "schedule": "0 */2 * * *",  # Every 2 hours
        "schedule_description": "Every 2 hours",
        "tables": [],  # User selects tables
        "requires_table_selection": True,
        "transformations": [],  # No default transformations
        "estimated_rows_per_day": 10000,
        "use_cases": [
            "Create read replicas for analytics",
            "Offload reporting queries",
            "Data backup to warehouse",
            "Cross-region data sync",
        ],
        "config_options": {
            "sync_mode": {
                "type": "select",
                "options": ["full_refresh", "incremental"],
                "default": "incremental",
                "description": "Sync mode for data transfer",
            },
            "incremental_key": {
                "type": "text",
                "default": "updated_at",
                "description": "Column to use for incremental sync",
            },
        },
    },
    "mongodb_collection_sync": {
        "name": "MongoDB Collection Sync",
        "description": "Sync MongoDB collections to a relational warehouse with schema flattening",
        "category": "operations",
        "source_type": "mongodb",
        "destination_type": None,
        "icon": "leaf",
        "schedule": "0 */3 * * *",  # Every 3 hours
        "schedule_description": "Every 3 hours",
        "tables": [],  # User selects collections
        "requires_table_selection": True,
        "transformations": [
            {
                "name": "Flatten Nested Documents",
                "description": "Flatten nested JSON into relational columns (customize per collection)",
                "sql": """
-- Example: Flatten user documents
-- Customize this query based on your collection structure
SELECT
    _id,
    name,
    email,
    profile->>'avatar' as avatar_url,
    profile->>'bio' as bio,
    CAST(profile->>'age' AS INTEGER) as age,
    created_at,
    updated_at
FROM mongo_users
""",
                "target_table": "users_flat",
                "execution_order": 1,
            },
        ],
        "estimated_rows_per_day": 5000,
        "use_cases": [
            "Convert NoSQL to relational for BI tools",
            "Create analytics-friendly schemas",
            "Archive MongoDB data",
            "Enable SQL queries on MongoDB data",
        ],
        "config_options": {
            "flatten_depth": {
                "type": "number",
                "default": 2,
                "description": "Maximum depth for JSON flattening",
            },
        },
    },
}


def get_recipe_by_id(recipe_id: str) -> Dict[str, Any] | None:
    """Get a recipe by its ID."""
    return PIPELINE_RECIPES.get(recipe_id)


def get_recipes_by_category(category: str) -> List[Dict[str, Any]]:
    """Get all recipes in a category."""
    return [
        {"id": recipe_id, **recipe}
        for recipe_id, recipe in PIPELINE_RECIPES.items()
        if recipe["category"] == category
    ]


def get_recipes_by_source_type(source_type: str) -> List[Dict[str, Any]]:
    """Get all recipes that use a specific source type."""
    return [
        {"id": recipe_id, **recipe}
        for recipe_id, recipe in PIPELINE_RECIPES.items()
        if recipe["source_type"] == source_type.lower()
    ]


def get_all_recipes() -> List[Dict[str, Any]]:
    """Get all recipes with their IDs."""
    return [
        {"id": recipe_id, **recipe}
        for recipe_id, recipe in PIPELINE_RECIPES.items()
    ]


def get_all_categories() -> Dict[str, Dict[str, str]]:
    """Get all recipe categories."""
    return RECIPE_CATEGORIES
