"""
Pydantic schemas for API request/response validation.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, computed_field, model_validator, model_serializer


import re

# ISO 8601 datetime pattern: YYYY-MM-DDTHH:MM:SS (with optional fractional seconds)
_ISO_DATETIME_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?$')


class UTCDatetimeMixin:
    """Mixin to serialize all datetime fields with UTC 'Z' suffix."""

    @model_serializer(mode='wrap', when_used='always')
    def _serialize_with_utc_datetimes(self, serializer, info):
        """Wrap serializer to add UTC 'Z' suffix to all datetime fields."""
        data = serializer(self)

        # Find and fix all datetime fields
        for key, value in data.items():
            if isinstance(value, str) and _ISO_DATETIME_PATTERN.match(value):
                # Confirmed ISO datetime string without timezone - add Z for UTC
                data[key] = value + 'Z'

        return data


# Auth Schemas
class TokenData(BaseModel):
    """Token payload schema."""
    user_id: Optional[int] = None


class UserLogin(BaseModel):
    """User login request schema."""
    email: EmailStr
    password: str


# User Schemas
class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
    username: str
    full_name: Optional[str] = None


class UserCreate(UserBase):
    """User creation schema."""
    password: str
    organization_id: int


class UserUpdate(BaseModel):
    """User update schema."""
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    """User response schema."""
    id: int
    organization_id: int
    is_active: bool
    is_superuser: bool
    two_factor_enabled: bool = False
    last_login: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    roles: list[str] = []

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_with_roles(cls, user):
        """Create response with roles from ORM user object."""
        data = {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "organization_id": user.organization_id,
            "is_active": user.is_active,
            "is_superuser": user.is_superuser,
            "two_factor_enabled": user.two_factor_enabled,
            "last_login": user.last_login,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "roles": [ur.role.slug for ur in user.user_roles] if user.user_roles else [],
        }
        return cls(**data)


class Token(BaseModel):
    """Token response schema."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# Organization Schemas
class OrganizationBase(BaseModel):
    """Base organization schema."""
    name: str
    slug: str
    description: Optional[str] = None


class OrganizationCreate(OrganizationBase):
    """Organization creation schema."""
    pass


class OrganizationUpdate(BaseModel):
    """Organization update schema."""
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class OrganizationResponse(OrganizationBase):
    """Organization response schema."""
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Data Source Schemas
class DataSourceBase(BaseModel):
    """Base data source schema."""
    name: str
    description: Optional[str] = None
    source_type: str
    config: Dict[str, Any]


class DataSourceCreate(DataSourceBase):
    """Data source creation schema."""
    organization_id: int

    @model_validator(mode='after')
    def validate_config(self):
        """Validate data source config based on source type."""
        source_type = self.source_type
        config = self.config

        if not source_type:
            return self

        # Validate REST API source config
        if source_type == "rest_api":
            required_fields = ["base_url", "endpoints"]
            missing = [f for f in required_fields if not config.get(f)]
            if missing:
                raise ValueError(f"REST API source requires: {', '.join(missing)}")

            # Validate endpoints
            endpoints = config.get("endpoints", [])
            if not isinstance(endpoints, list) or len(endpoints) == 0:
                raise ValueError("REST API source requires at least one endpoint")

            for i, endpoint in enumerate(endpoints):
                if not isinstance(endpoint, dict):
                    raise ValueError(f"Endpoint {i} must be a dictionary")
                if not endpoint.get("name"):
                    raise ValueError(f"Endpoint {i} missing 'name'")
                if not endpoint.get("path"):
                    raise ValueError(f"Endpoint {i} missing 'path'")

            # Validate pagination config if provided
            pagination_type = config.get("pagination_type")
            if pagination_type and pagination_type not in ["none", "page", "offset", "cursor", "link_header", "token", "next_url"]:
                raise ValueError(f"Invalid pagination_type: {pagination_type}")

            pagination_config = config.get("pagination_config", {})
            if pagination_type == "page":
                page_size = pagination_config.get("page_size")
                if page_size and (not isinstance(page_size, int) or page_size <= 0 or page_size > 1000):
                    raise ValueError("page_size must be between 1 and 1000")
            elif pagination_type == "offset":
                limit = pagination_config.get("limit")
                if limit and (not isinstance(limit, int) or limit <= 0 or limit > 1000):
                    raise ValueError("limit must be between 1 and 1000")

            # Validate auth config if provided
            auth_type = config.get("auth_type")
            if auth_type and auth_type not in ["none", "api_key", "bearer", "oauth2", "basic"]:
                raise ValueError(f"Invalid auth_type: {auth_type}")

        # Validate WhatsApp Business source config
        elif source_type == "whatsapp_business":
            required_fields = ["access_token", "phone_number_id", "business_account_id"]
            missing = [f for f in required_fields if not config.get(f)]
            if missing:
                raise ValueError(f"WhatsApp Business source requires: {', '.join(missing)}")

        # Validate Postgres source config
        elif source_type == "postgres":
            required_fields = ["host", "database", "user", "password"]
            missing = [f for f in required_fields if not config.get(f)]
            if missing:
                raise ValueError(f"Postgres source requires: {', '.join(missing)}")

        # Validate Paystack source config
        elif source_type == "paystack":
            if not config.get("secret_key"):
                raise ValueError("Paystack source requires: secret_key")

        # Validate Google Sheets source config
        elif source_type == "google_sheets":
            required_fields = ["credentials_json", "spreadsheet_id"]
            missing = [f for f in required_fields if not config.get(f)]
            if missing:
                raise ValueError(f"Google Sheets source requires: {', '.join(missing)}")

        return self


class DataSourceUpdate(BaseModel):
    """Data source update schema."""
    name: Optional[str] = None
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class DataSourceResponse(UTCDatetimeMixin, DataSourceBase):
    """Data source response schema."""
    public_id: UUID
    organization_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def id(self) -> str:
        """Return public_id as string for id field."""
        return str(self.public_id)

    class Config:
        from_attributes = True


# Destination Schemas
class DestinationBase(BaseModel):
    """Base destination schema."""
    name: str
    description: Optional[str] = None
    destination_type: str
    config: Dict[str, Any]


class DestinationCreate(DestinationBase):
    """Destination creation schema."""
    organization_id: int

    @model_validator(mode='after')
    def validate_config(self):
        """Validate destination config based on destination type."""
        destination_type = self.destination_type
        config = self.config

        if not destination_type:
            return self

        # Validate S3 config
        if destination_type == "s3":
            required_fields = ["bucket_url"]
            missing = [f for f in required_fields if not config.get(f)]
            if missing:
                raise ValueError(f"S3 destination requires: {', '.join(missing)}")

            # Validate bucket URL format
            bucket_url = config.get("bucket_url", "")
            if not bucket_url.startswith("s3://"):
                raise ValueError("S3 bucket_url must start with 's3://'")

            # Optional but recommended: credentials
            if not config.get("aws_access_key_id") or not config.get("aws_secret_access_key"):
                # Allow environment credentials, but warn
                pass

            # Validate file format if provided
            file_format = config.get("file_format", "parquet")
            if file_format not in ["parquet", "jsonl", "csv", "insert_values"]:
                raise ValueError(f"Invalid file_format: {file_format}. Must be one of: parquet, jsonl, csv, insert_values")

        # Validate GCS config
        elif destination_type == "gcs":
            required_fields = ["bucket_url"]
            missing = [f for f in required_fields if not config.get(f)]
            if missing:
                raise ValueError(f"GCS destination requires: {', '.join(missing)}")

            bucket_url = config.get("bucket_url", "")
            if not bucket_url.startswith("gs://"):
                raise ValueError("GCS bucket_url must start with 'gs://'")

            file_format = config.get("file_format", "parquet")
            if file_format not in ["parquet", "jsonl", "csv", "insert_values"]:
                raise ValueError(f"Invalid file_format: {file_format}")

        # Validate Azure Blob config
        elif destination_type == "azure_blob":
            required_fields = ["bucket_url"]
            missing = [f for f in required_fields if not config.get(f)]
            if missing:
                raise ValueError(f"Azure Blob destination requires: {', '.join(missing)}")

            bucket_url = config.get("bucket_url", "")
            if not (bucket_url.startswith("az://") or bucket_url.startswith("abfs://")):
                raise ValueError("Azure bucket_url must start with 'az://' or 'abfs://'")

            file_format = config.get("file_format", "parquet")
            if file_format not in ["parquet", "jsonl", "csv", "insert_values"]:
                raise ValueError(f"Invalid file_format: {file_format}")

        # Validate database destinations
        elif destination_type in ["postgres", "mysql"]:
            required_fields = ["host", "database", "user", "password"]
            missing = [f for f in required_fields if not config.get(f)]
            if missing:
                raise ValueError(f"{destination_type.upper()} destination requires: {', '.join(missing)}")

        elif destination_type == "snowflake":
            # Snowflake requires account/host, database, username, password, warehouse
            required_fields = ["database", "username", "password", "warehouse"]
            missing = [f for f in required_fields if not config.get(f)]
            if missing:
                raise ValueError(f"Snowflake destination requires: {', '.join(missing)}")

            # Must have either host or account
            if not config.get("host") and not config.get("account"):
                raise ValueError("Snowflake destination requires 'host' or 'account' (e.g., xy12345.us-east-1)")

            if not config.get("dataset_name"):
                config["dataset_name"] = "default"

        elif destination_type in ["bigquery", "redshift"]:
            # These have complex credential requirements, just check dataset_name
            if not config.get("dataset_name"):
                config["dataset_name"] = "default"

        return self


class DestinationUpdate(BaseModel):
    """Destination update schema."""
    name: Optional[str] = None
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class DestinationResponse(UTCDatetimeMixin, DestinationBase):
    """Destination response schema."""
    public_id: UUID
    organization_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def id(self) -> str:
        """Return public_id as string for id field."""
        return str(self.public_id)

    class Config:
        from_attributes = True


# Pipeline Schemas
class PipelineBase(BaseModel):
    """Base pipeline schema."""
    name: str
    description: Optional[str] = None
    schedule: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    max_retries: Optional[int] = 0
    retry_delay_seconds: Optional[int] = 60
    exponential_backoff_enabled: Optional[bool] = False


class PipelineCreate(PipelineBase):
    """Pipeline creation schema."""
    organization_id: int
    source_id: str  # Accept UUID string
    destination_id: str  # Accept UUID string


class PipelineUpdate(BaseModel):
    """Pipeline update schema."""
    name: Optional[str] = None
    description: Optional[str] = None
    schedule: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class PipelineResponse(UTCDatetimeMixin, PipelineBase):
    """Pipeline response schema."""
    public_id: UUID
    organization_id: int
    source_id: int
    destination_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def id(self) -> str:
        """Return public_id as string for id field."""
        return str(self.public_id)

    class Config:
        from_attributes = True


# Pipeline Run Schemas
class PipelineRunCreate(BaseModel):
    """Pipeline run creation schema."""
    pipeline_id: int


class PipelineRunUpdate(BaseModel):
    """Pipeline run update schema."""
    status: Optional[str] = None
    rows_read: Optional[int] = None
    rows_written: Optional[int] = None
    bytes_read: Optional[int] = None
    bytes_written: Optional[int] = None
    error_message: Optional[str] = None
    error_traceback: Optional[str] = None
    run_metadata: Optional[Dict[str, Any]] = None  # Changed from 'metadata' to match database column


class PipelineRunResponse(UTCDatetimeMixin, BaseModel):
    """Pipeline run response schema."""
    public_id: UUID
    pipeline_id: int
    status: str
    retry_count: int = 0
    is_retry: bool = False
    original_run_id: Optional[int] = None
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    rows_read: Optional[int]
    rows_written: Optional[int]
    bytes_read: Optional[int]
    bytes_written: Optional[int]
    duration_seconds: Optional[float]
    error_message: Optional[str]
    error_traceback: Optional[str]
    run_metadata: Optional[Dict[str, Any]]  # Changed from 'metadata' to match database column
    created_at: datetime

    @computed_field
    @property
    def id(self) -> str:
        """Return public_id as string for id field."""
        return str(self.public_id)

    class Config:
        from_attributes = True


# Lineage Schemas
class LineageNodeBase(BaseModel):
    """Base lineage node schema."""
    node_type: str
    name: str
    database_name: Optional[str] = None
    schema_name: Optional[str] = None
    table_name: Optional[str] = None
    column_name: Optional[str] = None
    description: Optional[str] = None
    data_type: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None


class LineageNodeCreate(LineageNodeBase):
    """Lineage node creation schema."""
    fqn: str


class LineageNodeResponse(LineageNodeBase):
    """Lineage node response schema."""
    id: int
    fqn: str
    created_at: datetime
    updated_at: datetime
    last_seen_at: datetime

    class Config:
        from_attributes = True


class LineageEdgeBase(BaseModel):
    """Base lineage edge schema."""
    transformation_type: Optional[str] = None
    transformation_logic: Optional[str] = None
    description: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None


class LineageEdgeCreate(LineageEdgeBase):
    """Lineage edge creation schema."""
    source_node_id: int
    target_node_id: int


class LineageEdgeResponse(LineageEdgeBase):
    """Lineage edge response schema."""
    id: int
    source_node_id: int
    target_node_id: int
    created_at: datetime
    updated_at: datetime
    last_seen_at: datetime

    class Config:
        from_attributes = True


class LineageGraphResponse(BaseModel):
    """Lineage graph response schema."""
    nodes: List[LineageNodeResponse]
    edges: List[LineageEdgeResponse]


# Pagination
class PaginatedResponse(BaseModel):
    """Generic paginated response."""
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int
