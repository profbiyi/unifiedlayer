"""
Sync template definitions.

Static list of pre-built pipeline templates for one-click deployment.
"""

TEMPLATES = [
    {
        "id": "flutterwave-postgres",
        "name": "Flutterwave to PostgreSQL",
        "description": "Sync Flutterwave transactions, transfers, and settlements into PostgreSQL for analytics.",
        "category": "payments",
        "source_type": "flutterwave",
        "destination_type": "postgres",
        "icon": "wallet",
        "tags": ["payments", "flutterwave", "africa", "postgres", "analytics"],
        "source_config_template": {
            "secret_key": "",
            "environment": "sandbox",
        },
        "destination_config_template": {
            "host": "",
            "port": 5432,
            "database": "",
            "username": "",
            "password": "",
            "dataset_name": "flutterwave_data",
        },
        "source_credential_schema": [
            {"field": "secret_key", "label": "Secret Key", "type": "password", "placeholder": "FLWSECK_TEST-...", "required": True},
            {"field": "environment", "label": "Environment", "type": "select", "options": ["sandbox", "production"], "required": True},
        ],
        "destination_credential_schema": [
            {"field": "host", "label": "Host", "type": "text", "placeholder": "localhost", "required": True},
            {"field": "port", "label": "Port", "type": "number", "placeholder": "5432", "required": False},
            {"field": "database", "label": "Database", "type": "text", "placeholder": "analytics", "required": True},
            {"field": "username", "label": "Username", "type": "text", "placeholder": "postgres", "required": True},
            {"field": "password", "label": "Password", "type": "password", "placeholder": "", "required": True},
        ],
    },
    {
        "id": "paystack-postgres",
        "name": "Paystack to PostgreSQL",
        "description": "Sync Paystack transactions, customers, and settlements into PostgreSQL.",
        "category": "payments",
        "source_type": "paystack",
        "destination_type": "postgres",
        "icon": "credit-card",
        "tags": ["payments", "paystack", "nigeria", "postgres"],
        "source_config_template": {
            "secret_key": "",
        },
        "destination_config_template": {
            "host": "",
            "port": 5432,
            "database": "",
            "username": "",
            "password": "",
            "dataset_name": "paystack_data",
        },
        "source_credential_schema": [
            {"field": "secret_key", "label": "Secret Key", "type": "password", "placeholder": "sk_live_...", "required": True},
        ],
        "destination_credential_schema": [
            {"field": "host", "label": "Host", "type": "text", "placeholder": "localhost", "required": True},
            {"field": "port", "label": "Port", "type": "number", "placeholder": "5432", "required": False},
            {"field": "database", "label": "Database", "type": "text", "placeholder": "analytics", "required": True},
            {"field": "username", "label": "Username", "type": "text", "placeholder": "postgres", "required": True},
            {"field": "password", "label": "Password", "type": "password", "placeholder": "", "required": True},
        ],
    },
    {
        "id": "mpesa-bigquery",
        "name": "M-Pesa to BigQuery",
        "description": "Load M-Pesa mobile money transactions into Google BigQuery for advanced analytics.",
        "category": "payments",
        "source_type": "mpesa",
        "destination_type": "bigquery",
        "icon": "smartphone",
        "tags": ["payments", "mpesa", "kenya", "bigquery", "mobile-money"],
        "source_config_template": {
            "consumer_key": "",
            "consumer_secret": "",
            "environment": "sandbox",
            "shortcode": "",
        },
        "destination_config_template": {
            "credentials_json": {},
            "dataset_name": "mpesa_data",
        },
        "source_credential_schema": [
            {"field": "consumer_key", "label": "Consumer Key", "type": "text", "placeholder": "", "required": True},
            {"field": "consumer_secret", "label": "Consumer Secret", "type": "password", "placeholder": "", "required": True},
            {"field": "environment", "label": "Environment", "type": "select", "options": ["sandbox", "production"], "required": True},
            {"field": "shortcode", "label": "Business Shortcode", "type": "text", "placeholder": "174379", "required": False},
        ],
        "destination_credential_schema": [
            {"field": "credentials_json", "label": "Service Account JSON", "type": "textarea", "placeholder": '{"type": "service_account", ...}', "required": True},
            {"field": "dataset_name", "label": "Dataset Name", "type": "text", "placeholder": "mpesa_data", "required": False},
        ],
    },
    {
        "id": "rest-api-postgres",
        "name": "REST API to PostgreSQL",
        "description": "Pull data from any REST API endpoint and load it into PostgreSQL.",
        "category": "api",
        "source_type": "rest_api",
        "destination_type": "postgres",
        "icon": "globe",
        "tags": ["api", "rest", "postgres", "generic"],
        "source_config_template": {
            "base_url": "",
            "endpoints": [{"name": "data", "path": "/"}],
            "auth_type": "none",
        },
        "destination_config_template": {
            "host": "",
            "port": 5432,
            "database": "",
            "username": "",
            "password": "",
            "dataset_name": "api_data",
        },
        "source_credential_schema": [
            {"field": "base_url", "label": "Base URL", "type": "text", "placeholder": "https://api.example.com", "required": True},
            {"field": "auth_type", "label": "Auth Type", "type": "select", "options": ["none", "bearer", "api_key", "basic"], "required": False},
            {"field": "auth_token", "label": "Auth Token / API Key", "type": "password", "placeholder": "", "required": False},
        ],
        "destination_credential_schema": [
            {"field": "host", "label": "Host", "type": "text", "placeholder": "localhost", "required": True},
            {"field": "port", "label": "Port", "type": "number", "placeholder": "5432", "required": False},
            {"field": "database", "label": "Database", "type": "text", "placeholder": "analytics", "required": True},
            {"field": "username", "label": "Username", "type": "text", "placeholder": "postgres", "required": True},
            {"field": "password", "label": "Password", "type": "password", "placeholder": "", "required": True},
        ],
    },
    {
        "id": "postgres-bigquery",
        "name": "PostgreSQL to BigQuery",
        "description": "Replicate your PostgreSQL database tables into Google BigQuery for warehousing.",
        "category": "database",
        "source_type": "postgres",
        "destination_type": "bigquery",
        "icon": "database",
        "tags": ["database", "postgres", "bigquery", "warehouse"],
        "source_config_template": {
            "host": "",
            "port": 5432,
            "database": "",
            "user": "",
            "password": "",
        },
        "destination_config_template": {
            "credentials_json": {},
            "dataset_name": "postgres_replica",
        },
        "source_credential_schema": [
            {"field": "host", "label": "Host", "type": "text", "placeholder": "localhost", "required": True},
            {"field": "port", "label": "Port", "type": "number", "placeholder": "5432", "required": False},
            {"field": "database", "label": "Database", "type": "text", "placeholder": "mydb", "required": True},
            {"field": "user", "label": "Username", "type": "text", "placeholder": "postgres", "required": True},
            {"field": "password", "label": "Password", "type": "password", "placeholder": "", "required": True},
        ],
        "destination_credential_schema": [
            {"field": "credentials_json", "label": "Service Account JSON", "type": "textarea", "placeholder": '{"type": "service_account", ...}', "required": True},
            {"field": "dataset_name", "label": "Dataset Name", "type": "text", "placeholder": "postgres_replica", "required": False},
        ],
    },
    {
        "id": "mtn-momo-postgres",
        "name": "MTN MoMo to PostgreSQL",
        "description": "Sync MTN Mobile Money collections, disbursements, and balances into PostgreSQL.",
        "category": "payments",
        "source_type": "mtn_momo",
        "destination_type": "postgres",
        "icon": "smartphone",
        "tags": ["payments", "mtn", "mobile-money", "africa", "postgres"],
        "source_config_template": {
            "subscription_key": "",
            "api_user": "",
            "api_key": "",
            "environment": "sandbox",
        },
        "destination_config_template": {
            "host": "",
            "port": 5432,
            "database": "",
            "username": "",
            "password": "",
            "dataset_name": "mtn_momo_data",
        },
        "source_credential_schema": [
            {"field": "subscription_key", "label": "Subscription Key", "type": "password", "placeholder": "", "required": True},
            {"field": "api_user", "label": "API User", "type": "text", "placeholder": "X-Reference-Id", "required": True},
            {"field": "api_key", "label": "API Key", "type": "password", "placeholder": "", "required": True},
            {"field": "environment", "label": "Environment", "type": "select", "options": ["sandbox", "production"], "required": True},
        ],
        "destination_credential_schema": [
            {"field": "host", "label": "Host", "type": "text", "placeholder": "localhost", "required": True},
            {"field": "port", "label": "Port", "type": "number", "placeholder": "5432", "required": False},
            {"field": "database", "label": "Database", "type": "text", "placeholder": "analytics", "required": True},
            {"field": "username", "label": "Username", "type": "text", "placeholder": "postgres", "required": True},
            {"field": "password", "label": "Password", "type": "password", "placeholder": "", "required": True},
        ],
    },
    {
        "id": "mysql-postgres",
        "name": "MySQL to PostgreSQL",
        "description": "Migrate or replicate your MySQL database into PostgreSQL.",
        "category": "database",
        "source_type": "mysql",
        "destination_type": "postgres",
        "icon": "database",
        "tags": ["database", "mysql", "postgres", "migration"],
        "source_config_template": {
            "host": "",
            "port": 3306,
            "database": "",
            "user": "",
            "password": "",
        },
        "destination_config_template": {
            "host": "",
            "port": 5432,
            "database": "",
            "username": "",
            "password": "",
            "dataset_name": "mysql_replica",
        },
        "source_credential_schema": [
            {"field": "host", "label": "Host", "type": "text", "placeholder": "localhost", "required": True},
            {"field": "port", "label": "Port", "type": "number", "placeholder": "3306", "required": False},
            {"field": "database", "label": "Database", "type": "text", "placeholder": "mydb", "required": True},
            {"field": "user", "label": "Username", "type": "text", "placeholder": "root", "required": True},
            {"field": "password", "label": "Password", "type": "password", "placeholder": "", "required": True},
        ],
        "destination_credential_schema": [
            {"field": "host", "label": "Host", "type": "text", "placeholder": "localhost", "required": True},
            {"field": "port", "label": "Port", "type": "number", "placeholder": "5432", "required": False},
            {"field": "database", "label": "Database", "type": "text", "placeholder": "analytics", "required": True},
            {"field": "username", "label": "Username", "type": "text", "placeholder": "postgres", "required": True},
            {"field": "password", "label": "Password", "type": "password", "placeholder": "", "required": True},
        ],
    },
    {
        "id": "whatsapp-postgres",
        "name": "WhatsApp Business to PostgreSQL",
        "description": "Sync WhatsApp Business messages and contacts into PostgreSQL for CRM analytics.",
        "category": "messaging",
        "source_type": "whatsapp",
        "destination_type": "postgres",
        "icon": "message-circle",
        "tags": ["messaging", "whatsapp", "postgres", "crm"],
        "source_config_template": {
            "access_token": "",
            "phone_number_id": "",
            "business_account_id": "",
        },
        "destination_config_template": {
            "host": "",
            "port": 5432,
            "database": "",
            "username": "",
            "password": "",
            "dataset_name": "whatsapp_data",
        },
        "source_credential_schema": [
            {"field": "access_token", "label": "Access Token", "type": "password", "placeholder": "", "required": True},
            {"field": "phone_number_id", "label": "Phone Number ID", "type": "text", "placeholder": "", "required": True},
            {"field": "business_account_id", "label": "Business Account ID", "type": "text", "placeholder": "", "required": True},
        ],
        "destination_credential_schema": [
            {"field": "host", "label": "Host", "type": "text", "placeholder": "localhost", "required": True},
            {"field": "port", "label": "Port", "type": "number", "placeholder": "5432", "required": False},
            {"field": "database", "label": "Database", "type": "text", "placeholder": "analytics", "required": True},
            {"field": "username", "label": "Username", "type": "text", "placeholder": "postgres", "required": True},
            {"field": "password", "label": "Password", "type": "password", "placeholder": "", "required": True},
        ],
    },
    {
        "id": "google-sheets-postgres",
        "name": "Google Sheets to PostgreSQL",
        "description": "Import data from Google Spreadsheets into PostgreSQL. Perfect for SMEs tracking data in sheets.",
        "category": "productivity",
        "source_type": "google_sheets",
        "destination_type": "postgres",
        "icon": "table",
        "tags": ["productivity", "google-sheets", "postgres", "spreadsheet"],
        "source_config_template": {
            "credentials_json": "",
            "spreadsheet_id": "",
        },
        "destination_config_template": {
            "host": "",
            "port": 5432,
            "database": "",
            "username": "",
            "password": "",
            "dataset_name": "sheets_data",
        },
        "source_credential_schema": [
            {"field": "credentials_json", "label": "Service Account JSON", "type": "textarea", "placeholder": '{"type": "service_account", ...}', "required": True},
            {"field": "spreadsheet_id", "label": "Spreadsheet ID", "type": "text", "placeholder": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms", "required": True},
        ],
        "destination_credential_schema": [
            {"field": "host", "label": "Host", "type": "text", "placeholder": "localhost", "required": True},
            {"field": "port", "label": "Port", "type": "number", "placeholder": "5432", "required": False},
            {"field": "database", "label": "Database", "type": "text", "placeholder": "analytics", "required": True},
            {"field": "username", "label": "Username", "type": "text", "placeholder": "postgres", "required": True},
            {"field": "password", "label": "Password", "type": "password", "placeholder": "", "required": True},
        ],
    },
    {
        "id": "paystack-bigquery",
        "name": "Paystack to BigQuery",
        "description": "Load Paystack payment data into BigQuery for advanced financial analytics.",
        "category": "payments",
        "source_type": "paystack",
        "destination_type": "bigquery",
        "icon": "credit-card",
        "tags": ["payments", "paystack", "bigquery", "nigeria", "analytics"],
        "source_config_template": {
            "secret_key": "",
        },
        "destination_config_template": {
            "credentials_json": {},
            "dataset_name": "paystack_data",
        },
        "source_credential_schema": [
            {"field": "secret_key", "label": "Secret Key", "type": "password", "placeholder": "sk_live_...", "required": True},
        ],
        "destination_credential_schema": [
            {"field": "credentials_json", "label": "Service Account JSON", "type": "textarea", "placeholder": '{"type": "service_account", ...}', "required": True},
            {"field": "dataset_name", "label": "Dataset Name", "type": "text", "placeholder": "paystack_data", "required": False},
        ],
    },
]


def get_all_templates():
    """Return all available templates."""
    return TEMPLATES


def get_template_by_id(template_id: str):
    """Return a single template by ID, or None."""
    for template in TEMPLATES:
        if template["id"] == template_id:
            return template
    return None


def get_templates_by_category(category: str):
    """Return templates filtered by category."""
    return [t for t in TEMPLATES if t["category"] == category]


def get_categories():
    """Return unique category list."""
    return list(set(t["category"] for t in TEMPLATES))
