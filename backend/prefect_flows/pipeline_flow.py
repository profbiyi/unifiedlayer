"""
Prefect flows for pipeline execution.

Provides orchestration for data pipeline runs using Prefect.
"""
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import dlt
from prefect import flow, task
import logging
import traceback

from backend.database import get_db_session
from backend.models.pipeline import Pipeline, PipelineRun, PipelineStatus
from backend.models.quality import PipelineQualityCheck, QualityCheckResult, QualityCheckSeverity, QualityCheckStatus
from backend.notifications import email_notifier, slack_notifier
from backend.utils.quality_validators import execute_quality_check
from backend.services.retry_handler import handle_pipeline_failure
import uuid
import time

logger = logging.getLogger(__name__)

# Sensitive keys that should be redacted from logs
SENSITIVE_KEYS = {"password", "secret", "api_key", "token", "credentials", "secret_key", "access_key", "private_key"}


def sanitize_for_logging(config: dict) -> dict:
    """
    Remove sensitive values from config for safe logging.

    Args:
        config: Configuration dictionary that may contain sensitive values

    Returns:
        Sanitized copy of the config with sensitive values replaced by "***REDACTED***"
    """
    if not isinstance(config, dict):
        return config

    sanitized = {}
    for key, value in config.items():
        if any(s in key.lower() for s in SENSITIVE_KEYS):
            sanitized[key] = "***REDACTED***"
        elif isinstance(value, dict):
            sanitized[key] = sanitize_for_logging(value)
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_for_logging(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            sanitized[key] = value
    return sanitized


def _get_write_disposition(write_mode: str) -> Any:
    """Convert Pipeline write_mode to dlt write_disposition."""
    if write_mode == "scd2":
        return {"disposition": "merge", "strategy": "scd2"}
    if write_mode == "merge":
        return "merge"
    if write_mode == "replace":
        return "replace"
    return "append"  # default for "append" and unknown values


def _get_schema_contract(schema_contract: str) -> dict:
    """Convert Pipeline schema_contract to dlt schema_contract config."""
    return {
        "tables": "evolve",       # always allow new tables
        "columns": schema_contract,   # user-controlled column policy
        "data_type": "discard_rows" if schema_contract == "freeze" else "evolve",
    }



@task(retries=3, retry_delay_seconds=60)
def fetch_source_data(source_config: Dict[str, Any], source_type: str):
    """
    Fetch data from source using appropriate connector.

    Args:
        source_config: Source configuration
        source_type: Type of source (postgres, mysql, mpesa, etc.)

    Returns:
        dlt source object
    """
    logger.info(f"Fetching data from source type: {source_type}")
    logger.info(f"Source config keys: {list(source_config.keys())}")

    # Import appropriate connector
    if source_type == "postgres":
        # Attempt to use ConnectorX backend for 5-10x faster extraction.
        # ConnectorX reads via Arrow zero-copy, so it's significantly faster than
        # the default sqlalchemy row-by-row path. Falls back gracefully if not installed.
        try:
            import connectorx as _cx  # noqa: F401 — just checking availability
            _connectorx_backend = "connectorx"
            logger.info("Using ConnectorX backend for fast postgres extraction")
        except ImportError:
            _connectorx_backend = "sqlalchemy"
            logger.info("ConnectorX not installed, using sqlalchemy backend for postgres")

        from backend.connectors.postgres import postgres_source
        # Transform config: username -> user (for compatibility with dlt connector)
        config = source_config.copy()
        if "username" in config and "user" not in config:
            config["user"] = config.pop("username")

        # Remove parameters that the connector doesn't accept
        # Keep only: host, port, database, user, password, schema, sslmode
        connector_params = {}
        param_mapping = {
            "host": "host",
            "port": "port",
            "database": "database",
            "user": "user",
            "password": "password",
            "schema": "schema",
            "sslmode": "sslmode",
        }
        for config_key, connector_key in param_mapping.items():
            if config_key in config:
                connector_params[connector_key] = config[config_key]

        # For Neon databases, extract endpoint ID from host and add to options
        host = config.get("host", "")
        if "neon.tech" in host:
            # Extract endpoint ID (first part before first dot)
            # e.g., ep-round-violet-82034066-pooler.us-east-2.aws.neon.tech -> ep-round-violet-82034066-pooler
            endpoint_id = host.split(".")[0]
            connector_params["options"] = f"endpoint={endpoint_id}"
            logger.info(f"Detected Neon database, using endpoint: {endpoint_id}")

        # If ConnectorX is available, try using dlt sql_database with connectorx backend
        # for Arrow-accelerated extraction. Fall back to the custom postgres_source on error.
        if _connectorx_backend == "connectorx":
            try:
                from dlt.sources.sql_database import sql_database as _sql_db
                _sslmode = connector_params.get("sslmode", "prefer")
                _port = connector_params.get("port", 5432)
                _schema = connector_params.get("schema", "public")
                _cx_conn = (
                    f"postgresql://{connector_params['user']}:{connector_params['password']}"
                    f"@{connector_params['host']}:{_port}/{connector_params['database']}"
                    f"?sslmode={_sslmode}"
                )
                source = _sql_db(
                    credentials=_cx_conn,
                    schema=_schema,
                    backend="connectorx",
                )
                logger.info("ConnectorX sql_database source created successfully for postgres")
            except Exception as _cx_err:
                logger.warning(
                    "ConnectorX sql_database source creation failed (%s), "
                    "falling back to custom postgres_source", _cx_err
                )
                # Get tables list separately
                tables = config.get("tables", [])
                source = postgres_source(**connector_params)
        else:
            # Get tables list separately
            tables = config.get("tables", [])
            source = postgres_source(**connector_params)

    elif source_type == "mysql":
        # Attempt to use ConnectorX backend for 5-10x faster extraction.
        try:
            import connectorx as _cx  # noqa: F401 — just checking availability
            _connectorx_backend = "connectorx"
            logger.info("Using ConnectorX backend for fast mysql extraction")
        except ImportError:
            _connectorx_backend = "sqlalchemy"
            logger.info("ConnectorX not installed, using sqlalchemy backend for mysql")

        if _connectorx_backend == "connectorx":
            try:
                from dlt.sources.sql_database import sql_database as _sql_db
                _port = source_config.get("port", 3306)
                _user = source_config.get("user") or source_config.get("username") or source_config.get("user")
                _password = source_config.get("password", "")
                _host = source_config.get("host", "localhost")
                _database = source_config.get("database", "")
                _cx_conn = (
                    f"mysql://{_user}:{_password}@{_host}:{_port}/{_database}"
                )
                source = _sql_db(
                    credentials=_cx_conn,
                    backend="connectorx",
                )
                logger.info("ConnectorX sql_database source created successfully for mysql")
            except Exception as _cx_err:
                logger.warning(
                    "ConnectorX sql_database source creation failed (%s), "
                    "falling back to custom mysql_source", _cx_err
                )
                from backend.connectors.mysql import mysql_source
                source = mysql_source(**source_config)
        else:
            from backend.connectors.mysql import mysql_source
            source = mysql_source(**source_config)

    elif source_type == "mpesa":
        from backend.connectors.mpesa import mpesa_source
        source = mpesa_source(**source_config)

    elif source_type == "whatsapp":
        from backend.connectors.whatsapp_business import whatsapp_business_source
        source = whatsapp_business_source(**source_config)

    elif source_type == "paystack":
        from backend.connectors.paystack import paystack_source
        source = paystack_source(secret_key=source_config.get("secret_key"))

    elif source_type == "stripe":
        from backend.connectors.stripe_connector import stripe_source
        source = stripe_source(
            api_key=source_config.get("api_key"),
            tables=source_config.get("tables"),
        )

    elif source_type == "google_sheets":
        from backend.connectors.google_sheets import google_sheets_source
        source = google_sheets_source(
            credentials_json=source_config.get("credentials_json"),
            spreadsheet_id=source_config.get("spreadsheet_id"),
            sheets=source_config.get("sheets"),
        )

    elif source_type == "rest_api":
        from backend.connectors.rest_api import create_rest_api_source
        from urllib.parse import urlparse
        import re

        # Transform config to match rest_api_source signature
        config = source_config.copy()

        logger.info(f"Original REST API config: {config}")

        # Handle old format: {"url": "..."} -> {"base_url": "...", "endpoints": [...]}
        if "url" in config and "base_url" not in config:
            logger.info("Transforming old config format with 'url' to new format")

            # Parse the URL to separate base and path
            url = config.pop("url")
            parsed = urlparse(url)

            base_url = f"{parsed.scheme}://{parsed.netloc}"
            endpoint_path = parsed.path
            if parsed.query:
                endpoint_path += f"?{parsed.query}"

            config["base_url"] = base_url

            # Create endpoints list if not exists
            if "endpoints" not in config:
                # Extract endpoint name from path (e.g., /api/character -> character)
                path_parts = [p for p in endpoint_path.split('/') if p and p != 'api']
                endpoint_name = path_parts[-1] if path_parts else "api_data"
                endpoint_name = re.sub(r'[^a-zA-Z0-9_]', '_', endpoint_name).lower()

                config["endpoints"] = [
                    {
                        "name": endpoint_name,
                        "path": endpoint_path,
                        "data_path": config.get("data_path"),
                        "primary_key": config.get("primary_key", "id"),
                    }
                ]

                logger.info(f"Created endpoint: {config['endpoints'][0]}")

            # Remove old fields that connector doesn't expect at source level
            config.pop("data_path", None)
            config.pop("primary_key", None)

        # Filter config to only include valid parameters for rest_api_source
        valid_params = [
            "base_url", "endpoints", "auth_type", "auth_config",
            "pagination_type", "pagination_config", "rate_limit",
            "headers", "output_format", "retry_config",
            "async_mode", "max_concurrent"
        ]
        filtered_config = {k: v for k, v in config.items() if k in valid_params}

        # Check if we're already in an async context (Prefect may be running an event loop)
        # If so, disable async mode to avoid nested event loop issues
        import asyncio
        try:
            asyncio.get_running_loop()
            # We're in an async context, use sync mode to avoid nested loop issues
            in_async_context = True
            logger.info("Detected async context (Prefect), using sync mode for REST API")
        except RuntimeError:
            # No running event loop, safe to use async mode
            in_async_context = False

        # Enable async mode for better performance (unless in async context)
        # This allows multiple endpoints to be fetched concurrently
        if "async_mode" not in filtered_config:
            filtered_config["async_mode"] = not in_async_context
        if "max_concurrent" not in filtered_config:
            filtered_config["max_concurrent"] = 10

        logger.info(f"Filtered REST API config (async={filtered_config.get('async_mode')}): {filtered_config}")

        try:
            # Use factory function that automatically selects async or sync mode
            source = create_rest_api_source(**filtered_config)
        except TypeError as e:
            logger.error(f"Error creating REST API source: {e}")
            logger.error(f"Config keys: {list(filtered_config.keys())}")
            raise

    elif source_type == "gocardless":
        from backend.connectors.gocardless import GoCardlessConnector
        config = source_config.copy()
        connector = GoCardlessConnector(config)
        tables = config.get("tables", ["payments", "mandates", "customers", "payouts"])
        resources = []
        for table in tables:
            resources.extend(list(connector.extract(table)))
        # Wrap as dlt resource
        source = connector.to_dlt_resource(table_name=tables[0] if len(tables) == 1 else "payments")

    elif source_type == "xero":
        from backend.connectors.xero import XeroConnector
        config = source_config.copy()
        connector = XeroConnector(config)
        source = connector.to_dlt_resource(
            table_name=config.get("table", "invoices")
        )

    elif source_type == "open_banking":
        from backend.connectors.open_banking import OpenBankingConnector
        config = source_config.copy()
        connector = OpenBankingConnector(config)
        source = connector.to_dlt_resource(
            table_name=config.get("table", "transactions")
        )

    elif source_type == "hmrc_mtd":
        from backend.connectors.hmrc_mtd import HMRCMTDConnector
        config = source_config.copy()
        connector = HMRCMTDConnector(config)
        source = connector.to_dlt_resource(
            table_name=config.get("table", "vat_obligations")
        )

    elif source_type == "flutterwave":
        from backend.connectors.flutterwave import FlutterwaveConnector
        config = source_config.copy()
        connector = FlutterwaveConnector(config)
        source = connector.to_dlt_resource(
            table_name=config.get("table", "transactions")
        )

    elif source_type == "mtn_momo":
        from backend.connectors.mtn_momo import MTNMoMoConnector
        config = source_config.copy()
        connector = MTNMoMoConnector(config)
        source = connector.to_dlt_resource(
            table_name=config.get("table", "collections")
        )

    elif source_type == "mongodb":
        from backend.connectors.mongodb import MongoDBConnector
        config = source_config.copy()
        connector = MongoDBConnector(config)
        source = connector.to_dlt_resource(
            table_name=config.get("collection", config.get("table", "documents"))
        )

    elif source_type == "http_file":
        from backend.connectors.http_file_connector import create_http_file_source
        source, table_name = create_http_file_source(source_config)
        # http_file always uses replace (full reload each sync)

    elif source_type == "rest_api_declarative":
        from backend.connectors.rest_api_declarative import create_rest_api_source
        source = create_rest_api_source(source_config)

    else:
        raise ValueError(f"Unsupported source type: {source_type}")

    # Log source information
    logger.info(f"Source created: {type(source)}")
    if hasattr(source, 'resources'):
        logger.info(f"Source resources: {list(source.resources.keys()) if hasattr(source.resources, 'keys') else source.resources}")

    # Try to peek at the data to verify it exists
    try:
        # Get resource names
        if hasattr(source, 'selected_resources'):
            selected = list(source.selected_resources.keys())
            logger.info(f"Selected resources: {selected}")
    except Exception as e:
        logger.warning(f"Could not inspect source resources: {e}")

    return source


def sanitize_pipeline_name(name: str) -> str:
    """
    Sanitize pipeline name for use with dlt.

    dlt uses the pipeline name in SQL identifiers, so we need to:
    - Replace special characters with underscores
    - Ensure it starts with a letter
    - Keep only alphanumeric and underscores

    Args:
        name: Original pipeline name

    Returns:
        Sanitized pipeline name safe for SQL identifiers
    """
    import re
    # Replace common special chars with underscores
    sanitized = re.sub(r'[→\-\s/\\@#$%^&*()+=\[\]{}|;:\'",.<>?!~`]+', '_', name)
    # Keep only alphanumeric and underscores
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '', sanitized)
    # Collapse multiple underscores
    sanitized = re.sub(r'_+', '_', sanitized)
    # Remove leading/trailing underscores
    sanitized = sanitized.strip('_')
    # Ensure it starts with a letter
    if sanitized and not sanitized[0].isalpha():
        sanitized = 'pipeline_' + sanitized
    # Fallback if empty
    if not sanitized:
        sanitized = 'pipeline'
    return sanitized.lower()


@task(retries=2, retry_delay_seconds=30, timeout_seconds=3600)
def load_to_destination(
    source,
    destination_config: Dict[str, Any],
    destination_type: str,
    pipeline_name: str,
) -> Dict[str, Any]:
    """
    Load data to destination.

    Args:
        source: dlt source
        destination_config: Destination configuration
        destination_type: Type of destination
        pipeline_name: Name of the pipeline

    Returns:
        Load statistics
    """
    # Sanitize pipeline name for dlt (SQL-safe identifier)
    safe_pipeline_name = sanitize_pipeline_name(pipeline_name)
    logger.info(f"Loading data to destination type: {destination_type}, pipeline: {safe_pipeline_name}")

    # Handle filesystem destinations (S3, GCS, Azure Blob)
    if destination_type in ["s3", "gcs", "azure_blob"]:
        logger.info("Using filesystem destination for object storage")

        # Extract filesystem-specific config
        file_format = destination_config.get("file_format", "parquet")
        bucket_url = destination_config.get("bucket_url")

        if not bucket_url:
            raise ValueError(f"bucket_url is required for {destination_type} destination")

        # Build credentials based on destination type
        credentials = {}
        if destination_type == "s3":
            credentials = {
                "aws_access_key_id": destination_config.get("aws_access_key_id"),
                "aws_secret_access_key": destination_config.get("aws_secret_access_key"),
            }
            # Optional: AWS region
            if destination_config.get("region"):
                credentials["region_name"] = destination_config["region"]

        elif destination_type == "gcs":
            # GCS can use service account JSON or application default credentials
            if destination_config.get("service_account_json"):
                credentials = destination_config["service_account_json"]

        elif destination_type == "azure_blob":
            credentials = {
                "azure_storage_account_name": destination_config.get("account_name"),
                "azure_storage_account_key": destination_config.get("account_key"),
            }

        # Create dlt pipeline with filesystem destination and bucket URL
        # For dlt filesystem destinations, pass bucket_url as the destination parameter
        pipeline = dlt.pipeline(
            pipeline_name=safe_pipeline_name,
            destination=dlt.destinations.filesystem(bucket_url=bucket_url, credentials=credentials),
            dataset_name=destination_config.get("dataset_name", "default"),
        )

        # Load data with file format
        load_info = pipeline.run(
            source,
            loader_file_format=file_format,
        )

    else:
        # Handle database/warehouse destinations (postgres, bigquery, snowflake, etc.)
        logger.info(f"Using database/warehouse destination: {destination_type}")

        # Build credentials based on destination type
        if destination_type == "postgres":
            logger.info("Configuring PostgreSQL destination with credentials from config")

            # Extract PostgreSQL credentials from destination_config
            # Handle both "username" and "user" field names
            postgres_credentials = {
                "database": destination_config.get("database"),
                "password": destination_config.get("password"),
                "username": destination_config.get("username") or destination_config.get("user"),
                "host": destination_config.get("host"),
                "port": destination_config.get("port", 5432),
            }

            logger.info(f"PostgreSQL config: host={postgres_credentials['host']}, database={postgres_credentials['database']}, user={postgres_credentials['username']}")

            # Check if this is a Neon PostgreSQL connection (needs SSL and no search_path)
            is_neon = "neon.tech" in postgres_credentials["host"]

            if is_neon:
                logger.info("Detected Neon PostgreSQL - using unpooled endpoint and SSL")
                # Neon pooler doesn't support search_path parameter
                # Solution: Replace pooler endpoint with unpooled endpoint

                # Convert pooler endpoint to unpooled
                # e.g., ep-XXX-pooler.region.aws.neon.tech -> ep-XXX.region.aws.neon.tech
                host = postgres_credentials['host']
                unpooled_host = host.replace('-pooler', '')

                logger.info(f"Using unpooled Neon endpoint: {unpooled_host}")

                # Build connection string with unpooled host and SSL
                connection_string = (
                    f"postgresql://{postgres_credentials['username']}:{postgres_credentials['password']}"
                    f"@{unpooled_host}:{postgres_credentials['port']}/{postgres_credentials['database']}"
                    f"?sslmode=require"
                )

                logger.info("Using Neon-compatible unpooled connection with SSL")

                # Create destination with connection string
                from dlt.destinations import postgres
                destination = postgres(credentials=connection_string)

            else:
                # Standard PostgreSQL connection
                destination = dlt.destinations.postgres(credentials=postgres_credentials)

            # Create dlt pipeline with explicit credentials
            pipeline = dlt.pipeline(
                pipeline_name=safe_pipeline_name,
                destination=destination,
                dataset_name=destination_config.get("dataset_name", "default"),
            )

        elif destination_type == "bigquery":
            # BigQuery credentials
            credentials = destination_config.get("credentials_json")
            pipeline = dlt.pipeline(
                pipeline_name=safe_pipeline_name,
                destination=dlt.destinations.bigquery(credentials=credentials),
                dataset_name=destination_config.get("dataset_name", "default"),
            )

        elif destination_type == "snowflake":
            # Snowflake credentials
            # Build account identifier from host or account field
            # dlt expects: account.region (e.g., xy12345.us-east-1)
            # User may provide: xy12345.us-east-1.snowflakecomputing.com or just xy12345.us-east-1
            host = destination_config.get("host") or destination_config.get("account")

            if not host:
                raise ValueError("Snowflake destination requires 'host' or 'account' field")

            # Extract account identifier from full hostname if needed
            if host.endswith(".snowflakecomputing.com"):
                host = host.replace(".snowflakecomputing.com", "")

            logger.info(f"Configuring Snowflake destination with account: {host}")

            snowflake_credentials = {
                "database": destination_config.get("database"),
                "password": destination_config.get("password"),
                "username": destination_config.get("username") or destination_config.get("user"),
                "host": host,
                "warehouse": destination_config.get("warehouse"),
                "role": destination_config.get("role"),
            }

            # Remove None values to let dlt use defaults
            snowflake_credentials = {k: v for k, v in snowflake_credentials.items() if v is not None}

            pipeline = dlt.pipeline(
                pipeline_name=safe_pipeline_name,
                destination=dlt.destinations.snowflake(credentials=snowflake_credentials),
                dataset_name=destination_config.get("dataset_name", "default"),
            )

        elif destination_type == "duckdb":
            # DuckDB credentials
            database_path = destination_config.get("database_path", f"{safe_pipeline_name}.duckdb")
            logger.info(f"Configuring DuckDB destination at: {database_path}")

            pipeline = dlt.pipeline(
                pipeline_name=safe_pipeline_name,
                destination=dlt.destinations.duckdb(credentials=database_path),
                dataset_name=destination_config.get("dataset_name", "default"),
            )

        elif destination_type == "redshift":
            # Redshift credentials (similar to Postgres but with different port)
            redshift_credentials = {
                "database": destination_config.get("database"),
                "password": destination_config.get("password"),
                "username": destination_config.get("username") or destination_config.get("user"),
                "host": destination_config.get("host"),
                "port": destination_config.get("port", 5439),  # Redshift default
            }

            logger.info(f"Configuring Redshift destination at: {redshift_credentials['host']}")

            pipeline = dlt.pipeline(
                pipeline_name=safe_pipeline_name,
                destination=dlt.destinations.redshift(credentials=redshift_credentials),
                dataset_name=destination_config.get("dataset_name", "default"),
            )

        elif destination_type == "fabric":
            # Microsoft Fabric (OneLake / Lakehouse) via dlt filesystem destination
            # Credentials: workspace_id, lakehouse_name, and Azure credentials
            workspace_id = destination_config.get("workspace_id")
            lakehouse_name = destination_config.get("lakehouse_name", "UnifiedLayer")

            if not workspace_id:
                raise ValueError("Microsoft Fabric destination requires 'workspace_id' credential")

            # Build the OneLake ADLS Gen2 URL.
            # Format: abfss://<workspace_id>@onelake.dfs.fabric.microsoft.com/<lakehouse_name>.Lakehouse/Files/
            onelake_url = (
                f"abfss://{workspace_id}@onelake.dfs.fabric.microsoft.com"
                f"/{lakehouse_name}.Lakehouse/Files/"
            )
            logger.info(f"Configuring Microsoft Fabric destination at: {onelake_url}")

            azure_credentials = {
                "azure_storage_account_name": destination_config.get("account_name", "onelake"),
                "azure_storage_account_key": destination_config.get("account_key"),
                "azure_client_id": destination_config.get("client_id"),
                "azure_client_secret": destination_config.get("client_secret"),
                "azure_tenant_id": destination_config.get("tenant_id"),
            }
            # Remove None values so dlt can pick up env var fallbacks
            azure_credentials = {k: v for k, v in azure_credentials.items() if v is not None}

            file_format = destination_config.get("file_format", "parquet")

            try:
                pipeline = dlt.pipeline(
                    pipeline_name=safe_pipeline_name,
                    destination=dlt.destinations.filesystem(
                        bucket_url=onelake_url,
                        credentials=azure_credentials,
                    ),
                    dataset_name=destination_config.get("dataset_name", "default"),
                )
            except Exception as e:
                logger.error("Microsoft Fabric destination config failed: %s", e)
                raise

        else:
            # Fallback for other destinations (will try to use env vars)
            logger.warning(f"Using default destination setup for {destination_type} - may need environment variables")
            pipeline = dlt.pipeline(
                pipeline_name=safe_pipeline_name,
                destination=destination_type,
                dataset_name=destination_config.get("dataset_name", "default"),
            )

        # Load data with write_disposition and schema_contract
        # These are passed in via destination_config["_dlt_options"] if present.
        # The execute_pipeline_flow injects _dlt_options into the destination_config dict.
        _dlt_opts = destination_config.get("_dlt_options", {})
        _write_disposition = _dlt_opts.get("write_disposition", "merge")
        _schema_contract = _dlt_opts.get("schema_contract")

        if destination_type == "fabric":
            _run_kwargs: Dict[str, Any] = {"loader_file_format": file_format}
        else:
            _run_kwargs = {}

        if _schema_contract:
            _run_kwargs["schema_contract"] = _schema_contract

        load_info = pipeline.run(source, write_disposition=_write_disposition, **_run_kwargs)

    # Extract statistics from dlt load_info using helper
    from backend.utils.dlt_helpers import extract_load_stats

    stats = extract_load_stats(load_info, pipeline)

    # Remove internal extraction_method key before returning
    stats.pop("extraction_method", None)

    logger.info(f"Final load stats: {stats['rows_written']} rows, {stats['tables_loaded']} tables")
    return stats


@task
def update_run_progress(
    run_id: int,
    progress_percent: int,
    current_step: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Update pipeline run progress.

    Args:
        run_id: Pipeline run ID
        progress_percent: Progress percentage (0-100)
        current_step: Description of current step
        metadata: Additional metadata to merge
    """
    logger.info(f"Run {run_id} progress: {progress_percent}% - {current_step}")

    db = get_db_session()
    try:
        run = db.query(PipelineRun).filter(PipelineRun.id == run_id).first()

        if not run:
            logger.error(f"Pipeline run {run_id} not found")
            return

        # Update or initialize run_metadata
        if run.run_metadata is None:
            run.run_metadata = {}

        run.run_metadata["progress_percent"] = progress_percent
        run.run_metadata["current_step"] = current_step
        run.run_metadata["last_updated"] = datetime.now(timezone.utc).isoformat()

        # Merge additional metadata if provided
        if metadata:
            run.run_metadata.update(metadata)

        db.commit()

    finally:
        db.close()


@task
def update_pipeline_run(
    run_id: int,
    status: str,
    stats: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
    error_traceback: Optional[str] = None,
) -> None:
    """
    Update pipeline run status.

    Args:
        run_id: Pipeline run ID
        status: New status
        stats: Load statistics
        error: Error message (if failed)
        error_traceback: Full error traceback (if failed)
    """
    logger.info(f"Updating run {run_id} to status: {status}")

    db = get_db_session()
    try:
        run = db.query(PipelineRun).filter(PipelineRun.id == run_id).first()

        if not run:
            logger.error(f"Pipeline run {run_id} not found")
            return

        run.status = status

        if status == "running":
            run.started_at = datetime.now(timezone.utc)
            # Initialize metadata
            if run.run_metadata is None:
                run.run_metadata = {}
            run.run_metadata["progress_percent"] = 0
            run.run_metadata["current_step"] = "Starting pipeline execution"

        elif status in ["completed", "failed", "cancelled"]:
            run.completed_at = datetime.now(timezone.utc)

            if run.started_at:
                # Ensure both timestamps are timezone-aware for subtraction
                started_at = run.started_at
                if started_at.tzinfo is None:
                    # Make naive datetime aware (assume UTC)
                    started_at = started_at.replace(tzinfo=timezone.utc)

                duration = (run.completed_at - started_at).total_seconds()
                run.duration_seconds = duration

            # Update progress to 100% if completed
            if status == "completed":
                if run.run_metadata is None:
                    run.run_metadata = {}
                run.run_metadata["progress_percent"] = 100
                run.run_metadata["current_step"] = "Completed successfully"

        if stats:
            run.rows_written = stats.get("rows_written", 0)
            run.bytes_written = stats.get("bytes_written", 0)
            # Store stats in metadata
            if run.run_metadata is None:
                run.run_metadata = {}
            run.run_metadata["stats"] = stats

        if error:
            run.error_message = error[:1000]  # Limit to 1000 chars for error message

        if error_traceback:
            run.error_traceback = error_traceback[:5000]  # Limit to 5000 chars for traceback

        db.commit()

    finally:
        db.close()


@task
def send_notifications(
    pipeline_name: str,
    run_id: int,
    status: str,
    stats: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
) -> None:
    """
    Send notifications about pipeline run.

    Args:
        pipeline_name: Name of the pipeline
        run_id: Pipeline run ID
        status: Run status
        stats: Load statistics
        error: Error message (if failed)
    """
    logger.info(f"Sending notifications for run {run_id}")

    db = get_db_session()
    try:
        # Get pipeline run details
        from backend.models.user import User

        run = db.query(PipelineRun).filter(PipelineRun.id == run_id).first()
        if not run:
            logger.error(f"Pipeline run {run_id} not found")
            return

        pipeline = db.query(Pipeline).filter(Pipeline.id == run.pipeline_id).first()
        if not pipeline:
            logger.error(f"Pipeline {run.pipeline_id} not found")
            return

        # Get organization admin email for notifications
        # TODO: In the future, support per-user notification preferences
        admin_user = (
            db.query(User)
            .filter(User.organization_id == pipeline.organization_id)
            .first()
        )

        if not admin_user or not admin_user.email:
            logger.warning(f"No admin user found for organization {pipeline.organization_id}")
            # Still send Slack notifications
        else:
            # Generate frontend URL for pipeline
            from backend.config import settings
            frontend_url = settings.FRONTEND_URL
            pipeline_url = f"{frontend_url}/pipelines/{pipeline.public_id}"

            # Get organization for branding
            org = pipeline.organization if pipeline.organization else None

            if status == "completed":
                # Success notification
                rows_processed = stats.get("rows_written", 0) if stats else 0
                duration = run.duration_seconds if run.duration_seconds else 0.0

                # Send email notification with branding
                try:
                    email_notifier.send_pipeline_success_email(
                        to_email=admin_user.email,
                        pipeline_name=pipeline_name,
                        run_id=run_id,
                        records_processed=rows_processed,
                        duration_seconds=duration,
                        pipeline_url=pipeline_url,
                        organization_name=org.name if org else None,
                        logo_url=org.logo_url if org else None,
                        brand_primary_color=org.brand_primary_color if org else None,
                        brand_secondary_color=org.brand_secondary_color if org else None,
                    )
                    logger.info(f"Success email sent to {admin_user.email}")
                except Exception as e:
                    logger.error(f"Failed to send success email: {str(e)}")

                # Send Slack notification
                slack_notifier.send_pipeline_success(pipeline_name, run_id, rows_processed)

            elif status == "failed":
                # Failure notification
                error_msg = error or "Unknown error"
                error_tb = run.error_traceback or "No traceback available"

                # Send email notification with branding
                try:
                    email_notifier.send_pipeline_failure_email(
                        to_email=admin_user.email,
                        pipeline_name=pipeline_name,
                        run_id=run_id,
                        error_message=error_msg,
                        error_traceback=error_tb,
                        pipeline_url=pipeline_url,
                        organization_name=org.name if org else None,
                        logo_url=org.logo_url if org else None,
                        brand_primary_color=org.brand_primary_color if org else None,
                        brand_secondary_color=org.brand_secondary_color if org else None,
                    )
                    logger.info(f"Failure email sent to {admin_user.email}")
                except Exception as e:
                    logger.error(f"Failed to send failure email: {str(e)}")

                # Send Slack notification
                slack_notifier.send_pipeline_failure(pipeline_name, run_id, error_msg)

    except Exception as e:
        logger.error(f"Failed to send notifications: {str(e)}")
    finally:
        db.close()



@task
def run_quality_checks(
    pipeline_id: int,
    run_id: int,
    destination_table: str,
) -> Dict[str, Any]:
    """
    Run quality checks for a pipeline.

    Args:
        pipeline_id: Pipeline ID
        run_id: Pipeline run ID
        destination_table: Name of the destination table to check

    Returns:
        Quality check summary with results
    """
    logger.info(f"Running quality checks for pipeline {pipeline_id}, run {run_id}")

    db = get_db_session()
    try:
        # Get all active quality checks for this pipeline
        pipeline_checks = (
            db.query(PipelineQualityCheck)
            .filter(
                PipelineQualityCheck.pipeline_id == pipeline_id,
                PipelineQualityCheck.is_active,
                PipelineQualityCheck.run_on_success,
            )
            .all()
        )

        if not pipeline_checks:
            logger.info(f"No quality checks configured for pipeline {pipeline_id}")
            return {
                "total_checks": 0,
                "passed": 0,
                "failed": 0,
                "errors": 0,
                "critical_failures": 0,
            }

        logger.info(f"Found {len(pipeline_checks)} quality checks to run")

        # Run each check
        results_summary = {
            "total_checks": len(pipeline_checks),
            "passed": 0,
            "failed": 0,
            "warnings": 0,
            "errors": 0,
            "critical_failures": 0,
            "check_results": [],
        }

        for pipeline_check in pipeline_checks:
            quality_check = pipeline_check.quality_check

            if not quality_check.is_active:
                logger.info(f"Skipping inactive check: {quality_check.name}")
                continue

            logger.info(f"Running check: {quality_check.name} ({quality_check.check_type})")

            # Execute the check
            start_time = time.time()
            try:
                check_result = execute_quality_check(
                    db=db,
                    check=quality_check,
                    table_name=destination_table,
                )
                execution_time = (time.time() - start_time) * 1000  # Convert to ms

                # Determine severity (use override if set)
                severity = pipeline_check.override_severity or quality_check.severity

                # Create result record
                result = QualityCheckResult(
                    public_id=uuid.uuid4(),
                    pipeline_run_id=run_id,
                    pipeline_check_id=pipeline_check.id,
                    status=check_result.status,
                    severity=severity,
                    passed=check_result.passed,
                    actual_value=check_result.actual_value,
                    expected_value=check_result.expected_value,
                    message=check_result.message,
                    details=check_result.details,
                    execution_time_ms=execution_time,
                    rows_checked=check_result.rows_checked,
                )

                db.add(result)
                db.flush()

                # Update summary
                if check_result.passed:
                    results_summary["passed"] += 1
                elif check_result.status == QualityCheckStatus.ERROR:
                    results_summary["errors"] += 1
                elif check_result.status == QualityCheckStatus.WARNING:
                    results_summary["warnings"] += 1
                else:
                    results_summary["failed"] += 1

                    # Track critical failures
                    if severity == QualityCheckSeverity.CRITICAL:
                        results_summary["critical_failures"] += 1

                # Add to results list
                results_summary["check_results"].append({
                    "check_name": quality_check.name,
                    "check_type": quality_check.check_type.value,
                    "severity": severity.value,
                    "passed": check_result.passed,
                    "status": check_result.status.value,
                    "message": check_result.message,
                    "execution_time_ms": execution_time,
                })

                logger.info(
                    f"Check '{quality_check.name}' {check_result.status.value}: {check_result.message}"
                )

            except Exception as e:
                logger.error(f"Error executing check '{quality_check.name}': {str(e)}", exc_info=True)

                # Create error result
                result = QualityCheckResult(
                    public_id=uuid.uuid4(),
                    pipeline_run_id=run_id,
                    pipeline_check_id=pipeline_check.id,
                    status=QualityCheckStatus.ERROR,
                    severity=pipeline_check.override_severity or quality_check.severity,
                    passed=False,
                    message=f"Error executing check: {str(e)}",
                    details={"error": str(e)},
                    execution_time_ms=(time.time() - start_time) * 1000,
                )

                db.add(result)
                results_summary["errors"] += 1

        db.commit()

        logger.info(
            f"Quality checks completed: {results_summary['passed']} passed, "
            f"{results_summary['failed']} failed, {results_summary['errors']} errors, "
            f"{results_summary['critical_failures']} critical failures"
        )

        return results_summary

    except Exception as e:
        logger.error(f"Failed to run quality checks: {str(e)}", exc_info=True)
        return {
            "total_checks": 0,
            "passed": 0,
            "failed": 0,
            "errors": 1,
            "critical_failures": 0,
            "error": str(e),
        }
    finally:
        db.close()


def _parse_error_message(error: str, traceback_str: str = "") -> str:
    """
    Parse error messages to create user-friendly descriptions.

    Handles common dlt errors, database errors, and connection issues.

    Args:
        error: Raw error message
        traceback_str: Full traceback string

    Returns:
        User-friendly error message
    """
    error_lower = error.lower()
    tb_lower = traceback_str.lower()

    # Snowflake errors
    if "snowflake" in error_lower or "snowflake" in tb_lower:
        if "syntax error" in error_lower:
            return "Snowflake SQL syntax error. This may be caused by special characters in the pipeline name or data. Please check your pipeline configuration."
        if "authentication" in error_lower or "password" in error_lower:
            return "Snowflake authentication failed. Please verify your account, username, and password are correct."
        if "warehouse" in error_lower:
            return "Snowflake warehouse error. Please verify the warehouse name exists and your user has access to it."
        if "database" in error_lower and "does not exist" in error_lower:
            return "The specified Snowflake database does not exist. Please create it first or check the name."
        if "schema" in error_lower and "does not exist" in error_lower:
            return "The specified Snowflake schema does not exist. Please create it first or check the name."

    # PostgreSQL errors
    if "postgres" in error_lower or "psycopg" in tb_lower:
        if "authentication failed" in error_lower:
            return "PostgreSQL authentication failed. Please verify your username and password."
        if "connection refused" in error_lower:
            return "Could not connect to PostgreSQL. Please verify the host and port are correct and the server is running."
        if "database" in error_lower and "does not exist" in error_lower:
            return "The specified PostgreSQL database does not exist."
        if "timeout" in error_lower:
            return "PostgreSQL connection timed out. The server may be slow or unreachable."

    # BigQuery errors
    if "bigquery" in error_lower or "google.cloud" in tb_lower:
        if "credentials" in error_lower or "authentication" in error_lower:
            return "BigQuery authentication failed. Please verify your service account credentials are correct."
        if "not found" in error_lower and "dataset" in error_lower:
            return "The specified BigQuery dataset was not found. Please create it first."
        if "permission" in error_lower or "access denied" in error_lower:
            return "Access denied to BigQuery. Please check your service account has the required permissions."

    # S3/AWS errors
    if "s3" in error_lower or "aws" in error_lower or "boto" in tb_lower:
        if "access denied" in error_lower or "403" in error_lower:
            return "Access denied to S3 bucket. Please verify your AWS credentials and bucket permissions."
        if "not found" in error_lower or "404" in error_lower:
            return "S3 bucket not found. Please verify the bucket name and region."
        if "invalid access key" in error_lower:
            return "Invalid AWS access key. Please check your credentials."

    # dlt specific errors
    if "dlt" in error_lower or "dlt" in tb_lower:
        if "configfieldmissing" in error_lower:
            # Extract the missing field
            import re
            match = re.search(r"missing field.*?:\s*[`'\"]?(\w+)[`'\"]?", error_lower)
            field = match.group(1) if match else "unknown"
            return f"Missing required configuration field: '{field}'. Please check your destination settings."
        if "load_id" in error_lower:
            return "Data loading failed. There may be an issue with the data format or destination schema. Try using a new dataset/schema."
        if "retry" in error_lower and "exceeded" in error_lower:
            return "Maximum retries exceeded during data loading. Please check your destination connection and try again."

    # Connection errors
    if "connection" in error_lower:
        if "refused" in error_lower:
            return "Connection refused. Please verify the host and port are correct and the service is running."
        if "timeout" in error_lower:
            return "Connection timed out. The destination may be slow or unreachable."
        if "reset" in error_lower:
            return "Connection was reset. Please try again."

    # Generic improvements
    if len(error) > 500:
        # Truncate very long errors but keep the important part
        first_line = error.split('\n')[0]
        if len(first_line) > 200:
            return first_line[:200] + "... (see full error in stack trace)"
        return first_line

    return error


@flow(name="Execute Data Pipeline", log_prints=True, timeout_seconds=1800)  # 30-minute timeout
def execute_pipeline_flow(pipeline_id: int, run_id: int) -> Dict[str, Any]:
    """
    Execute a data pipeline with comprehensive error handling and progress tracking.

    Args:
        pipeline_id: Pipeline ID
        run_id: Pipeline run ID

    Returns:
        Execution results
    """
    logger.info(f"Starting pipeline execution: pipeline_id={pipeline_id}, run_id={run_id}")

    db = get_db_session()
    try:
        # Get pipeline configuration
        pipeline = db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()

        if not pipeline:
            raise ValueError(f"Pipeline {pipeline_id} not found")

        # Update run to running
        update_pipeline_run(run_id, "running")

        try:
            # Step 1: Fetch source data (Progress: 0-50%)
            update_run_progress(
                run_id,
                progress_percent=10,
                current_step=f"Fetching data from {pipeline.source.source_type.value} source",
                metadata={
                    "source_type": pipeline.source.source_type.value,
                    "source_name": pipeline.source.name,
                }
            )

            source = fetch_source_data(
                pipeline.source.config,
                pipeline.source.source_type.value,
            )

            update_run_progress(
                run_id,
                progress_percent=50,
                current_step="Source data fetched successfully",
            )

            # Step 1.5: Apply transformations if configured (Progress: 50-55%)
            pipeline_config = pipeline.config or {}
            if pipeline_config.get("transformations"):
                update_run_progress(
                    run_id,
                    progress_percent=52,
                    current_step="Applying data transformations",
                )
                from backend.utils.transforms import apply_transformations
                source = apply_transformations(source, pipeline_config)
                logger.info("Data transformations applied to source stream")

            # Step 2: Load to destination (Progress: 50-90%)
            update_run_progress(
                run_id,
                progress_percent=60,
                current_step=f"Loading data to {pipeline.destination.destination_type.value} destination",
                metadata={
                    "destination_type": pipeline.destination.destination_type.value,
                    "destination_name": pipeline.destination.name,
                }
            )

            # Build dlt execution options from pipeline write_mode and schema_contract.
            # These are passed through destination_config so load_to_destination
            # can forward them to pipeline.run() without changing its signature.
            _dest_config = dict(pipeline.destination.config)
            _dest_config["_dlt_options"] = {
                "write_disposition": _get_write_disposition(
                    getattr(pipeline, "write_mode", None) or "merge"
                ),
                "schema_contract": _get_schema_contract(
                    getattr(pipeline, "schema_contract", None) or "evolve"
                ),
            }
            logger.info(
                "Pipeline write_mode=%s schema_contract=%s",
                getattr(pipeline, "write_mode", "merge"),
                getattr(pipeline, "schema_contract", "evolve"),
            )

            stats = load_to_destination(
                source,
                _dest_config,
                pipeline.destination.destination_type.value,
                pipeline.name,
            )

            update_run_progress(
                run_id,
                progress_percent=90,
                current_step="Data loaded successfully",
            )

            # Step 3: Run quality checks (Progress: 90-95%)
            update_run_progress(
                run_id,
                progress_percent=92,
                current_step="Running quality checks",
            )

            # Determine destination table name
            destination_table = pipeline.destination.config.get("table", pipeline.name)

            # Run quality checks
            quality_results = run_quality_checks(
                pipeline_id=pipeline_id,
                run_id=run_id,
                destination_table=destination_table,
            )

            # Check for critical failures
            if quality_results.get("critical_failures", 0) > 0:
                error_msg = (
                    f"Pipeline failed quality checks: {quality_results['critical_failures']} "
                    f"critical failure(s) out of {quality_results['total_checks']} checks"
                )
                logger.error(error_msg)

                # Update run to failed with quality check details
                update_pipeline_run(
                    run_id,
                    "failed",
                    error_message=error_msg,
                    stats={
                        **stats,
                        "quality_checks": quality_results,
                    }
                )

                raise ValueError(error_msg)

            # Add quality check results to stats
            stats["quality_checks"] = quality_results

            logger.info(
                f"Quality checks passed: {quality_results['passed']}/{quality_results['total_checks']} "
                f"(warnings: {quality_results.get('warnings', 0)}, errors: {quality_results.get('errors', 0)})"
            )

            # Step 4: Record lineage (Progress: 95-98%)
            update_run_progress(
                run_id,
                progress_percent=95,
                current_step="Recording data lineage",
            )

            # Record lineage for this pipeline execution
            try:
                from backend.services.lineage_service import LineageService
                lineage_service = LineageService(db)

                # Get tables that were loaded
                tables_loaded = [t["name"] for t in stats.get("tables", [])]
                if not tables_loaded:
                    # Fallback: use pipeline source config
                    tables_loaded = pipeline.source.config.get("tables", [pipeline.name])

                lineage_service.record_pipeline_lineage(
                    pipeline=pipeline,
                    tables_loaded=tables_loaded,
                    run_id=run_id,
                )
                logger.info(f"Lineage recorded for pipeline {pipeline.name}")
            except Exception as lineage_error:
                logger.warning(f"Failed to record lineage: {lineage_error}")
                # Don't fail the pipeline if lineage recording fails

            # Step 5: Auto-model if enabled (Progress: 95-98%)
            pipeline_config = pipeline.config or {}
            if pipeline_config.get("auto_model", False):
                update_run_progress(
                    run_id,
                    progress_percent=96,
                    current_step="Running AI auto-modeling",
                )

                try:
                    from backend.services.ai_modeler import get_ai_modeler
                    ai_modeler = get_ai_modeler()
                    modeling_result = ai_modeler.auto_model_pipeline(pipeline_id, db)

                    if modeling_result.error:
                        logger.warning(f"Auto-modeling completed with error: {modeling_result.error}")
                    else:
                        logger.info(
                            f"Auto-modeling completed: {len(modeling_result.canonical_models)} canonical, "
                            f"{len(modeling_result.dimensional_models)} dimensional models generated"
                        )
                        stats["auto_model"] = {
                            "canonical_models": len(modeling_result.canonical_models),
                            "dimensional_models": len(modeling_result.dimensional_models),
                            "business_questions": len(modeling_result.business_questions),
                        }
                except Exception as model_error:
                    logger.warning(f"Auto-modeling failed: {model_error}")
                    # Don't fail the pipeline if auto-modeling fails

            # Step 6: Finalize (Progress: 98-100%)
            update_run_progress(
                run_id,
                progress_percent=98,
                current_step="Finalizing pipeline run",
            )

            # Update run to completed
            update_pipeline_run(run_id, "completed", stats=stats)

            # Send success notifications
            send_notifications(pipeline.name, run_id, "completed", stats=stats)

            logger.info(f"Pipeline execution completed successfully: run_id={run_id}, stats={stats}")

            return {
                "status": "completed",
                "stats": stats,
                "run_id": run_id,
            }

        except Exception as e:
            # Capture full error details
            raw_error = str(e)
            error_tb = traceback.format_exc()

            # Parse error to create user-friendly message
            error_message = _parse_error_message(raw_error, error_tb)

            logger.error(
                f"Pipeline execution failed: run_id={run_id}, error={error_message}",
                exc_info=True
            )

            # Determine which step failed
            failed_step = "unknown"
            if "fetch" in raw_error.lower() or "source" in raw_error.lower():
                failed_step = "source_fetch"
            elif "load" in raw_error.lower() or "destination" in raw_error.lower():
                failed_step = "destination_load"
            elif "quality" in raw_error.lower() or "check" in raw_error.lower():
                failed_step = "quality_checks"

            # Update run to failed with full traceback
            update_pipeline_run(
                run_id,
                "failed",
                error=error_message,
                error_traceback=error_tb,
            )

            # Update progress with failure info
            update_run_progress(
                run_id,
                progress_percent=0,
                current_step=f"Failed at {failed_step}",
                metadata={
                    "failed_step": failed_step,
                    "error_type": type(e).__name__,
                }
            )

            # Send failure notifications
            send_notifications(pipeline.name, run_id, "failed", error=error_message)

            # Attempt to retry if configured
            retry_run_id = None
            try:
                retry_run_id = handle_pipeline_failure(
                    pipeline_id=pipeline_id,
                    run_id=run_id,
                    error_message=error_message,
                    retry_immediately=False,  # Use configured delay
                )
                if retry_run_id:
                    logger.info(f"Scheduled retry run {retry_run_id} for failed run {run_id}")
            except Exception as retry_error:
                logger.error(f"Failed to schedule retry: {str(retry_error)}", exc_info=True)

            return {
                "status": "failed",
                "error": error_message,
                "error_traceback": error_tb,
                "run_id": run_id,
                "failed_step": failed_step,
                "retry_run_id": retry_run_id,
            }

    finally:
        db.close()


@flow(name="Schedule Pipeline", log_prints=True)
def schedule_pipeline_flow(pipeline_id: int) -> None:
    """
    Schedule a pipeline for periodic execution.

    Args:
        pipeline_id: Pipeline ID
    """
    logger.info(f"Scheduling pipeline: {pipeline_id}")

    db = get_db_session()
    try:
        pipeline = db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()

        if not pipeline:
            logger.error(f"Pipeline {pipeline_id} not found")
            return

        if not pipeline.schedule:
            logger.warning(f"Pipeline {pipeline_id} has no schedule configured")
            return

        # Create pipeline run
        run = PipelineRun(
            pipeline_id=pipeline_id,
            status=PipelineStatus.PENDING,
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        # Execute pipeline
        execute_pipeline_flow(pipeline_id, run.id)

    finally:
        db.close()


if __name__ == "__main__":
    # Example: Execute a pipeline
    execute_pipeline_flow(pipeline_id=1, run_id=1)
