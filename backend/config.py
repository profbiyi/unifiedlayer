"""
Application configuration using Pydantic Settings.

Manages all environment variables and configuration for UnifiedLayer.
"""
from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All settings can be overridden via environment variables.
    """

    # Application
    APP_NAME: str = "UnifiedLayer"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = Field(default="development", description="Environment: development, staging, production")

    # API Server
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_WORKERS: int = 4
    CORS_ORIGINS: str = "*"  # Comma-separated list of allowed origins

    # Security
    SECRET_KEY: str = Field(..., description="Secret key for JWT tokens")
    ENCRYPTION_KEY: Optional[str] = Field(
        default=None,
        description="Fernet encryption key for config field encryption at rest. "
        "Generate with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Database
    DATABASE_URL: str = Field(
        ...,
        description="PostgreSQL database URL (e.g., postgresql://user:pass@localhost:5432/dbname)"
    )
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_ECHO: bool = False

    # Redis
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis URL for caching and queues"
    )
    REDIS_TTL: int = 3600

    # AWS Credentials
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    AWS_S3_BUCKET: Optional[str] = None

    # Azure Credentials (Optional)
    AZURE_STORAGE_CONNECTION_STRING: Optional[str] = None
    AZURE_STORAGE_CONTAINER: Optional[str] = None

    # GCP Credentials (Optional)
    GCP_PROJECT_ID: Optional[str] = None
    GCP_CREDENTIALS_PATH: Optional[str] = None
    GCS_BUCKET: Optional[str] = None

    # OpenAI
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4"
    OPENAI_TEMPERATURE: float = 0.7

    # Prefect
    PREFECT_API_URL: str = Field(
        default="http://localhost:4200/api",
        description="Prefect server API URL"
    )
    PREFECT_WORKSPACE: str = "default"

    # dlt Configuration
    DLT_PROJECT_DIR: str = "/app/dlt_data"
    DLT_DATA_DIR: str = "/app/dlt_data"
    DLT_PIPELINE_DIR: str = "/app/dlt_pipelines"

    # M-Pesa Connector
    MPESA_CONSUMER_KEY: Optional[str] = None
    MPESA_CONSUMER_SECRET: Optional[str] = None
    MPESA_ENVIRONMENT: str = "sandbox"
    MPESA_PASSKEY: Optional[str] = None
    MPESA_SHORTCODE: Optional[str] = None

    # WhatsApp Business Connector
    WHATSAPP_ACCESS_TOKEN: Optional[str] = None
    WHATSAPP_PHONE_NUMBER_ID: Optional[str] = None
    WHATSAPP_BUSINESS_ACCOUNT_ID: Optional[str] = None
    WHATSAPP_VERIFY_TOKEN: Optional[str] = None
    WHATSAPP_APP_SECRET: Optional[str] = None

    # PostgreSQL Source (for data extraction)
    POSTGRES_SOURCE_HOST: Optional[str] = None
    POSTGRES_SOURCE_PORT: int = 5432
    POSTGRES_SOURCE_DATABASE: Optional[str] = None
    POSTGRES_SOURCE_USER: Optional[str] = None
    POSTGRES_SOURCE_PASSWORD: Optional[str] = None
    POSTGRES_SOURCE_SCHEMA: str = "public"

    # MySQL Source (for data extraction)
    MYSQL_SOURCE_HOST: Optional[str] = None
    MYSQL_SOURCE_PORT: int = 3306
    MYSQL_SOURCE_DATABASE: Optional[str] = None
    MYSQL_SOURCE_USER: Optional[str] = None
    MYSQL_SOURCE_PASSWORD: Optional[str] = None

    # Monitoring & Observability
    PROMETHEUS_PORT: int = 9090
    GRAFANA_PORT: int = 3000
    GRAFANA_ADMIN_USER: str = Field(default="admin", description="Grafana admin username")
    GRAFANA_ADMIN_PASSWORD: Optional[str] = Field(default=None, description="Grafana admin password - set in production")

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    # Email Notifications
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: Optional[str] = None
    SMTP_USE_TLS: bool = True
    SENDGRID_API_KEY: Optional[str] = None  # If set, uses SendGrid API instead of SMTP

    # Frontend URL (for invitation links, etc.)
    FRONTEND_URL: str = "http://localhost"

    # Stripe Billing
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_PUBLISHABLE_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    STRIPE_PRICE_PROFESSIONAL: Optional[str] = None  # Stripe Price ID for Professional plan (GBP)
    STRIPE_PRICE_ENTERPRISE: Optional[str] = None  # Stripe Price ID for Enterprise plan (GBP)
    STRIPE_PRICE_PROFESSIONAL_EUR: Optional[str] = None  # Stripe Price ID for Professional plan (EUR €39)
    STRIPE_PRICE_ENTERPRISE_EUR: Optional[str] = None  # Stripe Price ID for Enterprise plan (EUR)

    # Paystack Billing (African payments - NGN, KES, GHS)
    PAYSTACK_SECRET_KEY: Optional[str] = None
    PAYSTACK_PUBLIC_KEY: Optional[str] = None
    PAYSTACK_WEBHOOK_SECRET: Optional[str] = None

    # Flutterwave Webhook
    FLUTTERWAVE_WEBHOOK_SECRET: Optional[str] = None

    # GoCardless Webhook
    GOCARDLESS_WEBHOOK_SECRET: Optional[str] = None

    # Xero OAuth
    XERO_CLIENT_ID: Optional[str] = None
    XERO_CLIENT_SECRET: Optional[str] = None

    # TrueLayer (Open Banking) OAuth
    TRUELAYER_CLIENT_ID: Optional[str] = None
    TRUELAYER_CLIENT_SECRET: Optional[str] = None

    # HMRC MTD OAuth
    HMRC_CLIENT_ID: Optional[str] = None
    HMRC_CLIENT_SECRET: Optional[str] = None

    # Google OAuth (User Authentication)
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: Optional[str] = None  # OAuth callback URL, e.g., http://localhost:8000/api/auth/google/callback

    # Slack Notifications
    SLACK_WEBHOOK_URL: Optional[str] = None
    SLACK_CHANNEL: Optional[str] = None

    # Twilio (WhatsApp Notifications via Twilio Sandbox / Business API)
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_WHATSAPP_FROM: Optional[str] = None  # e.g. "whatsapp:+14155238886" (Twilio sandbox number)

    # Anomaly Detection — comma-separated E.164 phone numbers to notify via WhatsApp
    # e.g. "+2348012345678,+447911123456"
    ANOMALY_WHATSAPP_NUMBERS: Optional[str] = None

    # Trino/Presto
    TRINO_HOST: str = "trino"
    TRINO_PORT: int = 8080
    TRINO_CATALOG: str = "duckdb"
    TRINO_SCHEMA: str = "main"

    # Data Quality
    DATA_QUALITY_ENABLED: bool = True
    DATA_QUALITY_THRESHOLD: float = 0.95

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 100

    # Trusted Proxies (comma-separated list of IP addresses/CIDRs)
    # Only trust X-Forwarded-For header from these IPs
    # Example: "10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,127.0.0.1"
    TRUSTED_PROXIES: Optional[str] = None

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v):
        """Validate database URL format."""
        if not v.startswith(("postgresql://", "postgresql+psycopg2://")):
            raise ValueError("DATABASE_URL must be a valid PostgreSQL connection string")
        return v

    def validate_production_settings(self) -> list[str]:
        """
        Validate settings for production deployment.

        Returns:
            List of warnings for insecure/missing settings
        """
        warnings = []

        if self.ENVIRONMENT == "production":
            if self.DEBUG:
                warnings.append("DEBUG should be False in production")
            if self.CORS_ORIGINS == "*":
                warnings.append("CORS_ORIGINS should not be '*' in production")
            if not self.GRAFANA_ADMIN_PASSWORD:
                warnings.append("GRAFANA_ADMIN_PASSWORD should be set in production")
            if self.FRONTEND_URL == "http://localhost":
                warnings.append("FRONTEND_URL should be set to production URL")
            if "localhost" in self.REDIS_URL:
                warnings.append("REDIS_URL should point to production Redis")
            if self.MPESA_ENVIRONMENT == "sandbox":
                warnings.append("MPESA_ENVIRONMENT should be 'production' for live transactions")

        return warnings

    @property
    def cors_origins_list(self):
        """Parse CORS_ORIGINS as a list."""
        if self.CORS_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    class Config:
        """Pydantic config."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # Ignore extra env vars not defined in Settings


# Global settings instance
settings = Settings()
