"""
Source Discovery API routes.

Endpoints for testing connections, discovering schemas, and previewing data.
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
import logging

from backend.database import get_db
from backend.models.pipeline import User
from backend.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sources/discovery", tags=["Source Discovery"])


class ConnectionTestRequest(BaseModel):
    """Request to test a source connection."""
    source_type: str
    config: Dict[str, Any]


class ConnectionTestResponse(BaseModel):
    """Response from connection test."""
    success: bool
    message: str
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class SchemaDiscoveryRequest(BaseModel):
    """Request to discover schemas/tables."""
    source_type: str
    config: Dict[str, Any]


class TableInfo(BaseModel):
    """Information about a discovered table."""
    schema: str
    table: str
    row_count: Optional[int] = None
    size_mb: Optional[float] = None
    columns: List[Dict[str, Any]] = []
    primary_keys: List[str] = []
    has_updated_at: bool = False


class SchemaDiscoveryResponse(BaseModel):
    """Response from schema discovery."""
    databases: List[str] = []
    schemas: List[str] = []
    tables: List[TableInfo] = []


class TablePreviewRequest(BaseModel):
    """Request to preview table data."""
    source_type: str
    config: Dict[str, Any]
    schema: str
    table: str
    limit: int = 10


class TablePreviewResponse(BaseModel):
    """Response from table preview."""
    columns: List[str]
    rows: List[List[Any]]
    total_rows: Optional[int] = None


@router.post("/test-connection", response_model=ConnectionTestResponse)
async def test_connection(
    request: ConnectionTestRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Test a source connection.

    Validates credentials and connectivity without storing configuration.
    """
    logger.info(f"Testing connection for source type: {request.source_type}")

    try:
        if request.source_type in ["postgres", "postgresql"]:
            result = await _test_postgres_connection(request.config)
        elif request.source_type == "mysql":
            result = await _test_mysql_connection(request.config)
        elif request.source_type == "mongodb":
            result = await _test_mongodb_connection(request.config)
        elif request.source_type == "s3":
            result = await _test_s3_connection(request.config)
        elif request.source_type == "rest_api":
            result = await _test_rest_api_connection(request.config)
        elif request.source_type in ["csv", "local"]:
            # File-based sources - just verify config exists
            result = ConnectionTestResponse(
                success=True,
                message="File configuration saved",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Connection testing not implemented for source type: {request.source_type}",
            )

        return result

    except Exception as e:
        logger.error(f"Connection test failed: {str(e)}", exc_info=True)
        return ConnectionTestResponse(
            success=False,
            message="Connection test failed",
            error=str(e),
        )


@router.post("/discover-schema", response_model=SchemaDiscoveryResponse)
async def discover_schema(
    request: SchemaDiscoveryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Discover schemas and tables from a source.

    Returns hierarchical structure of databases, schemas, and tables with metadata.
    """
    logger.info(f"Discovering schema for source type: {request.source_type}")

    try:
        if request.source_type in ["postgres", "postgresql"]:
            result = await _discover_postgres_schema(request.config)
        elif request.source_type == "mysql":
            result = await _discover_mysql_schema(request.config)
        elif request.source_type == "mongodb":
            result = await _discover_mongodb_schema(request.config)
        elif request.source_type == "rest_api":
            result = await _discover_rest_api_schema(request.config)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Schema discovery not implemented for source type: {request.source_type}",
            )

        return result

    except Exception as e:
        logger.error(f"Schema discovery failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Schema discovery failed: {str(e)}",
        )


@router.post("/preview-table", response_model=TablePreviewResponse)
async def preview_table(
    request: TablePreviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Preview sample data from a table.

    Returns first N rows for user to verify data structure.
    """
    logger.info(f"Previewing table: {request.schema}.{request.table}")

    try:
        if request.source_type in ["postgres", "postgresql"]:
            result = await _preview_postgres_table(
                request.config,
                request.schema,
                request.table,
                request.limit,
            )
        elif request.source_type == "mysql":
            result = await _preview_mysql_table(
                request.config,
                request.schema,
                request.table,
                request.limit,
            )
        elif request.source_type == "rest_api":
            result = await _preview_rest_api_table(
                request.config,
                request.schema,
                request.table,
                request.limit,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Table preview not implemented for source type: {request.source_type}",
            )

        return result

    except Exception as e:
        logger.error(f"Table preview failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Table preview failed: {str(e)}",
        )


# PostgreSQL Implementation
async def _test_postgres_connection(config: Dict[str, Any]) -> ConnectionTestResponse:
    """Test PostgreSQL connection."""
    import psycopg2
    from psycopg2 import OperationalError, DatabaseError

    try:
        logger.info(f"Testing PostgreSQL connection to {config.get('host')}:{config.get('port', 5432)}")

        # Build connection parameters
        conn_params = {
            "host": config.get("host"),
            "port": config.get("port", 5432),
            "database": config.get("database"),
            "user": config.get("username"),
            "password": config.get("password"),
            "connect_timeout": 30,  # Increased timeout for cloud databases
        }

        # Auto-detect Neon connection and set defaults
        host = config.get("host", "")
        if "neon.tech" in host.lower():
            # Auto-enable SSL for Neon
            if not config.get("sslmode"):
                conn_params["sslmode"] = "require"

            # Auto-detect endpoint ID if not provided
            if not config.get("options"):
                # Extract endpoint ID (first part of hostname before first dot)
                # e.g., "ep-cool-morning-123456.us-east-2.aws.neon.tech" -> "ep-cool-morning-123456"
                # or "ep-cool-morning-123456-pooler.us-east-2.aws.neon.tech" -> "ep-cool-morning-123456-pooler"
                endpoint_id = host.split(".")[0]
                # Keep the endpoint ID exactly as it appears in the hostname (including -pooler if present)
                conn_params["options"] = f"endpoint={endpoint_id}"
                logger.info(f"Auto-detected Neon endpoint: {endpoint_id}")
            else:
                # Use user-provided options
                conn_params["options"] = config.get("options")

        # Add SSL mode if specified for non-Neon databases
        if config.get("sslmode") and "neon.tech" not in host.lower():
            conn_params["sslmode"] = config.get("sslmode")

        # Add options if provided for non-Neon databases
        if config.get("options") and "neon.tech" not in host.lower():
            conn_params["options"] = config.get("options")

        conn = None
        try:
            conn = psycopg2.connect(**conn_params)

            # Get database version
            cursor = conn.cursor()
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]

            # Get database size
            cursor.execute("SELECT pg_database_size(current_database());")
            size_bytes = cursor.fetchone()[0]

            cursor.close()

            logger.info("PostgreSQL connection test successful")

            return ConnectionTestResponse(
                success=True,
                message="Successfully connected to PostgreSQL",
                metadata={
                    "version": version.split(",")[0],
                    "database_size_mb": round(size_bytes / 1024 / 1024, 2),
                    "database": config.get("database"),
                    "host": config.get("host"),
                },
            )
        finally:
            if conn:
                conn.close()

    except OperationalError as e:
        error_msg = str(e)
        logger.error(f"PostgreSQL connection failed: {error_msg}")

        # Provide more specific error messages
        if "authentication failed" in error_msg.lower():
            detailed_error = f"Authentication failed for user '{config.get('username')}'. Please check your username and password."
        elif "could not connect" in error_msg.lower() or "connection refused" in error_msg.lower():
            detailed_error = f"Could not connect to {config.get('host')}:{config.get('port', 5432)}. Please check the host and port are correct and the database is running."
        elif "database" in error_msg.lower() and "does not exist" in error_msg.lower():
            detailed_error = f"Database '{config.get('database')}' does not exist on the server."
        elif "timeout" in error_msg.lower():
            detailed_error = f"Connection timeout. The database server at {config.get('host')}:{config.get('port', 5432)} is not responding."
        else:
            detailed_error = f"Connection error: {error_msg}"

        return ConnectionTestResponse(
            success=False,
            message=detailed_error,
            error=error_msg,
        )

    except DatabaseError as e:
        error_msg = str(e)
        logger.error(f"PostgreSQL database error: {error_msg}")
        return ConnectionTestResponse(
            success=False,
            message=f"Database error: {error_msg}",
            error=error_msg,
        )

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Unexpected error testing PostgreSQL connection: {error_msg}", exc_info=True)
        return ConnectionTestResponse(
            success=False,
            message=f"Unexpected error: {error_msg}",
            error=error_msg,
        )


async def _discover_postgres_schema(config: Dict[str, Any]) -> SchemaDiscoveryResponse:
    """Discover PostgreSQL schema."""
    import psycopg2
    from psycopg2 import sql

    # Build connection parameters
    conn_params = {
        "host": config.get("host"),
        "port": config.get("port", 5432),
        "database": config.get("database"),
        "user": config.get("username"),
        "password": config.get("password"),
    }

    # Auto-detect Neon connection and set defaults
    host = config.get("host", "")
    if "neon.tech" in host.lower():
        # Auto-enable SSL for Neon
        if not config.get("sslmode"):
            conn_params["sslmode"] = "require"

        # Auto-detect endpoint ID if not provided
        if not config.get("options"):
            # Extract endpoint ID (first part of hostname before first dot)
            # e.g., "ep-cool-morning-123456.us-east-2.aws.neon.tech" -> "ep-cool-morning-123456"
            # or "ep-cool-morning-123456-pooler.us-east-2.aws.neon.tech" -> "ep-cool-morning-123456-pooler"
            endpoint_id = host.split(".")[0]
            # Keep the endpoint ID exactly as it appears in the hostname (including -pooler if present)
            conn_params["options"] = f"endpoint={endpoint_id}"
            logger.info(f"Auto-detected Neon endpoint for schema discovery: {endpoint_id}")
        else:
            # Use user-provided options
            conn_params["options"] = config.get("options")

    # Add SSL mode if specified for non-Neon databases
    if config.get("sslmode") and "neon.tech" not in host.lower():
        conn_params["sslmode"] = config.get("sslmode")

    # Add options if provided for non-Neon databases
    if config.get("options") and "neon.tech" not in host.lower():
        conn_params["options"] = config.get("options")

    conn = psycopg2.connect(**conn_params)

    cursor = conn.cursor()

    # Get all schemas (excluding system schemas)
    cursor.execute("""
        SELECT schema_name
        FROM information_schema.schemata
        WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast', 'pg_temp_1', 'pg_toast_temp_1')
        ORDER BY schema_name;
    """)
    schemas = [row[0] for row in cursor.fetchall()]
    logger.info(f"Found {len(schemas)} schemas: {schemas}")

    # Get all tables with metadata
    tables = []
    for schema in schemas:
        logger.info(f"Discovering tables in schema: {schema}")
        try:
            cursor.execute("""
                SELECT
                    table_schema,
                    table_name
                FROM information_schema.tables
                WHERE table_schema = %s AND table_type = 'BASE TABLE'
                ORDER BY table_name;
            """, (schema,))

            schema_tables = cursor.fetchall()
            logger.info(f"Found {len(schema_tables)} tables in schema '{schema}'")
        except Exception as e:
            logger.error(f"Error discovering tables in schema '{schema}': {e}")
            continue

        for row in schema_tables:
            table_schema, table_name = row

            # Get table size (may fail on some cloud providers)
            size_bytes = None
            try:
                cursor.execute("""
                    SELECT pg_total_relation_size(quote_ident(%s) || '.' || quote_ident(%s))
                """, (table_schema, table_name))
                size_result = cursor.fetchone()
                if size_result:
                    size_bytes = size_result[0]
            except Exception as e:
                logger.warning(f"Could not get size for {table_schema}.{table_name}: {e}")

            # Get columns
            cursor.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
                ORDER BY ordinal_position;
            """, (table_schema, table_name))

            columns = [
                {
                    "name": col[0],
                    "type": col[1],
                    "nullable": col[2] == "YES",
                }
                for col in cursor.fetchall()
            ]

            # Get primary keys
            primary_keys = []
            try:
                cursor.execute("""
                    SELECT a.attname
                    FROM pg_index i
                    JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
                    JOIN pg_class c ON c.oid = i.indrelid
                    JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE n.nspname = %s AND c.relname = %s
                    AND i.indisprimary;
                """, (table_schema, table_name))
                primary_keys = [row[0] for row in cursor.fetchall()]
            except Exception as e:
                logger.warning(f"Could not get primary keys for {table_schema}.{table_name}: {e}")

            # Check for updated_at column
            has_updated_at = any(
                col["name"] in ["updated_at", "modified_at", "last_modified"]
                for col in columns
            )

            # Get row count (exact count)
            try:
                # Use identifier quoting to prevent SQL injection
                cursor.execute(
                    sql.SQL("SELECT COUNT(*) FROM {}.{}").format(
                        sql.Identifier(table_schema),
                        sql.Identifier(table_name)
                    )
                )
                result = cursor.fetchone()
                row_count = result[0] if result else 0
            except Exception as e:
                logger.warning(f"Could not get row count for {table_schema}.{table_name}: {e}")
                row_count = 0

            # Convert size_bytes to size_mb
            size_mb = round(size_bytes / (1024 * 1024), 2) if size_bytes else None

            tables.append(TableInfo(
                schema=table_schema,
                table=table_name,
                row_count=row_count,
                size_mb=size_mb,
                columns=columns,
                primary_keys=primary_keys,
                has_updated_at=has_updated_at,
            ))

    cursor.close()
    conn.close()

    logger.info(f"Schema discovery complete: {len(schemas)} schemas, {len(tables)} tables")

    return SchemaDiscoveryResponse(
        databases=[config.get("database")],
        schemas=schemas,
        tables=tables,
    )


async def _preview_postgres_table(
    config: Dict[str, Any],
    schema: str,
    table: str,
    limit: int,
) -> TablePreviewResponse:
    """Preview PostgreSQL table data."""
    import psycopg2
    from psycopg2.extras import RealDictCursor

    conn = psycopg2.connect(
        host=config.get("host"),
        port=config.get("port", 5432),
        database=config.get("database"),
        user=config.get("username"),
        password=config.get("password"),
    )

    cursor = conn.cursor(cursor_factory=RealDictCursor)

    # Get total row count
    cursor.execute(f"SELECT COUNT(*) FROM {schema}.{table};")
    total_rows = cursor.fetchone()["count"]

    # Get sample data
    cursor.execute(f"SELECT * FROM {schema}.{table} LIMIT %s;", (limit,))
    rows = cursor.fetchall()

    columns = list(rows[0].keys()) if rows else []
    rows_data = [[row[col] for col in columns] for row in rows]

    cursor.close()
    conn.close()

    return TablePreviewResponse(
        columns=columns,
        rows=rows_data,
        total_rows=total_rows,
    )


# MySQL Implementation
async def _test_mysql_connection(config: Dict[str, Any]) -> ConnectionTestResponse:
    """Test MySQL connection."""
    import pymysql

    try:
        conn = pymysql.connect(
            host=config.get("host"),
            port=config.get("port", 3306),
            database=config.get("database"),
            user=config.get("username"),
            password=config.get("password"),
        )

        cursor = conn.cursor()
        cursor.execute("SELECT VERSION();")
        version = cursor.fetchone()[0]

        cursor.close()
        conn.close()

        return ConnectionTestResponse(
            success=True,
            message="Successfully connected to MySQL",
            metadata={"version": version},
        )

    except Exception as e:
        return ConnectionTestResponse(
            success=False,
            message="Failed to connect to MySQL",
            error=str(e),
        )


async def _discover_mysql_schema(config: Dict[str, Any]) -> SchemaDiscoveryResponse:
    """Discover MySQL schema."""
    import pymysql

    conn = pymysql.connect(
        host=config.get("host"),
        port=config.get("port", 3306),
        database=config.get("database"),
        user=config.get("username"),
        password=config.get("password"),
    )

    cursor = conn.cursor()

    # Get all tables
    cursor.execute("SHOW TABLES;")
    table_names = [row[0] for row in cursor.fetchall()]

    tables = []
    for table_name in table_names:
        # Get columns
        cursor.execute(f"DESCRIBE {table_name};")
        columns = [
            {
                "name": row[0],
                "type": row[1],
                "nullable": row[2] == "YES",
            }
            for row in cursor.fetchall()
        ]

        # Get row count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
        row_count = cursor.fetchone()[0]

        tables.append(TableInfo(
            schema=config.get("database"),
            table_name=table_name,
            row_count=row_count,
            columns=columns,
        ))

    cursor.close()
    conn.close()

    return SchemaDiscoveryResponse(
        databases=[config.get("database")],
        schemas=[config.get("database")],
        tables=tables,
    )


async def _preview_mysql_table(
    config: Dict[str, Any],
    schema: str,
    table: str,
    limit: int,
) -> TablePreviewResponse:
    """Preview MySQL table data."""
    import pymysql

    conn = pymysql.connect(
        host=config.get("host"),
        port=config.get("port", 3306),
        database=config.get("database"),
        user=config.get("username"),
        password=config.get("password"),
    )

    cursor = conn.cursor()

    # Get total row count
    cursor.execute(f"SELECT COUNT(*) FROM {table};")
    total_rows = cursor.fetchone()[0]

    # Get sample data
    cursor.execute(f"SELECT * FROM {table} LIMIT %s;", (limit,))
    rows = cursor.fetchall()

    # Get column names
    cursor.execute(f"DESCRIBE {table};")
    columns = [row[0] for row in cursor.fetchall()]

    cursor.close()
    conn.close()

    return TablePreviewResponse(
        columns=columns,
        rows=[list(row) for row in rows],
        total_rows=total_rows,
    )


# MongoDB Implementation
async def _test_mongodb_connection(config: Dict[str, Any]) -> ConnectionTestResponse:
    """Test MongoDB connection."""
    from pymongo import MongoClient

    try:
        client = MongoClient(config.get("connection_string"))
        # Test connection
        client.server_info()

        db_names = client.list_database_names()

        client.close()

        return ConnectionTestResponse(
            success=True,
            message="Successfully connected to MongoDB",
            metadata={"databases": db_names},
        )

    except Exception as e:
        return ConnectionTestResponse(
            success=False,
            message="Failed to connect to MongoDB",
            error=str(e),
        )


async def _discover_mongodb_schema(config: Dict[str, Any]) -> SchemaDiscoveryResponse:
    """Discover MongoDB schema."""
    from pymongo import MongoClient

    client = MongoClient(config.get("connection_string"))

    # Extract database name from connection string or use default
    db_name = config.get("database") or client.get_default_database().name
    db = client[db_name]

    collections = db.list_collection_names()

    tables = []
    for collection_name in collections:
        collection = db[collection_name]

        # Get document count
        count = collection.count_documents({})

        # Sample one document to infer schema
        sample = collection.find_one()
        columns = []
        if sample:
            for key, value in sample.items():
                columns.append({
                    "name": key,
                    "type": type(value).__name__,
                    "nullable": True,
                })

        tables.append(TableInfo(
            schema=db_name,
            table_name=collection_name,
            row_count=count,
            columns=columns,
        ))

    client.close()

    return SchemaDiscoveryResponse(
        databases=[db_name],
        schemas=[db_name],
        tables=tables,
    )


# S3 Implementation
async def _test_s3_connection(config: Dict[str, Any]) -> ConnectionTestResponse:
    """Test S3 connection."""
    import boto3
    from botocore.exceptions import ClientError

    try:
        s3 = boto3.client(
            "s3",
            aws_access_key_id=config.get("access_key"),
            aws_secret_access_key=config.get("secret_key"),
            region_name=config.get("region", "us-east-1"),
        )

        bucket = config.get("bucket")
        s3.head_bucket(Bucket=bucket)

        # Get bucket size
        response = s3.list_objects_v2(Bucket=bucket, MaxKeys=1000)
        objects_count = response.get("KeyCount", 0)

        return ConnectionTestResponse(
            success=True,
            message=f"Successfully connected to S3 bucket: {bucket}",
            metadata={"objects_count": objects_count},
        )

    except ClientError as e:
        return ConnectionTestResponse(
            success=False,
            message="Failed to connect to S3",
            error=str(e),
        )


# REST API Implementation
async def _test_rest_api_connection(config: Dict[str, Any]) -> ConnectionTestResponse:
    """Test REST API connection."""
    import httpx

    try:
        url = config.get("url")
        if not url:
            return ConnectionTestResponse(
                success=False,
                message="URL is required for REST API connection",
                error="Missing URL",
            )

        # Prepare headers
        headers = {}
        if config.get("auth_type") == "bearer":
            token = config.get("auth_token")
            if token:
                headers["Authorization"] = f"Bearer {token}"
        elif config.get("auth_type") == "api_key":
            key_name = config.get("auth_key_name", "X-API-Key")
            key_value = config.get("auth_key_value")
            if key_value:
                headers[key_name] = key_value

        # Make request
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()

            # Try to parse as JSON
            data = response.json()

            # Analyze structure
            data_path = None
            record_count = 0
            total_count = None
            detected_pagination = None

            if isinstance(data, list):
                data_path = "$"
                record_count = len(data)
            elif isinstance(data, dict):
                # Look for common data array keys
                for key in ["results", "data", "items", "records", "rows"]:
                    if key in data and isinstance(data[key], list):
                        data_path = key
                        record_count = len(data[key])
                        break

                # Try to detect total count
                for count_key in ["count", "total", "totalCount", "total_count"]:
                    if count_key in data:
                        total_count = data[count_key]
                        break

                # Check for nested count in info/meta
                if not total_count:
                    for meta_key in ["info", "meta", "metadata", "pagination"]:
                        if meta_key in data and isinstance(data[meta_key], dict):
                            for count_key in ["count", "total", "totalCount", "total_count"]:
                                if count_key in data[meta_key]:
                                    total_count = data[meta_key][count_key]
                                    break
                            if total_count:
                                break

                # Detect pagination type
                if "next" in data and data["next"]:
                    detected_pagination = "next_url"
                elif "info" in data and isinstance(data["info"], dict):
                    if "next" in data["info"]:
                        detected_pagination = "next_url"
                    elif "pages" in data["info"]:
                        detected_pagination = "page"
                elif any(k in data for k in ["pagination", "paging"]):
                    detected_pagination = "cursor"

            metadata = {
                "url": url,
                "status_code": response.status_code,
                "data_path": data_path,
                "record_count": record_count,
            }

            if total_count is not None:
                metadata["total_count"] = total_count
                metadata["note"] = f"Preview shows {record_count} records. Full sync will fetch all {total_count} records."

            if detected_pagination:
                metadata["detected_pagination"] = detected_pagination
                metadata["pagination_note"] = "Pagination detected. Configure pagination settings to fetch all records during sync."

            return ConnectionTestResponse(
                success=True,
                message="Successfully connected to REST API",
                metadata=metadata,
            )

    except httpx.HTTPStatusError as e:
        return ConnectionTestResponse(
            success=False,
            message=f"HTTP error {e.response.status_code}",
            error=str(e),
        )
    except httpx.RequestError as e:
        return ConnectionTestResponse(
            success=False,
            message=f"Connection error: {str(e)}",
            error=str(e),
        )
    except Exception as e:
        return ConnectionTestResponse(
            success=False,
            message=f"Failed to connect to REST API: {str(e)}",
            error=str(e),
        )


async def _discover_rest_api_schema(config: Dict[str, Any]) -> SchemaDiscoveryResponse:
    """Discover REST API schema by analyzing JSON structure."""
    import httpx

    url = config.get("url")

    # Prepare headers
    headers = {}
    if config.get("auth_type") == "bearer":
        token = config.get("auth_token")
        if token:
            headers["Authorization"] = f"Bearer {token}"
    elif config.get("auth_type") == "api_key":
        key_name = config.get("auth_key_name", "X-API-Key")
        key_value = config.get("auth_key_value")
        if key_value:
            headers[key_name] = key_value

    # Make request
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

    # Find the data array
    records = []
    data_path = None

    if isinstance(data, list):
        records = data[:10]  # Sample first 10 records
        data_path = "$"
    elif isinstance(data, dict):
        # Look for common data array keys
        for key in ["results", "data", "items", "records", "rows"]:
            if key in data and isinstance(data[key], list):
                records = data[key][:10]  # Sample first 10 records
                data_path = key
                break

    if not records:
        # No array found, treat the whole response as a single record
        records = [data]
        data_path = "$"

    # Analyze structure from sample records
    columns = []
    if records:
        # Get all unique keys from sample records
        all_keys = set()
        for record in records:
            if isinstance(record, dict):
                all_keys.update(record.keys())

        # Create column info
        for key in sorted(all_keys):
            # Infer type from first non-null value
            col_type = "string"
            for record in records:
                if isinstance(record, dict) and key in record:
                    value = record[key]
                    if value is not None:
                        if isinstance(value, bool):
                            col_type = "boolean"
                        elif isinstance(value, int):
                            col_type = "integer"
                        elif isinstance(value, float):
                            col_type = "number"
                        elif isinstance(value, dict):
                            col_type = "object"
                        elif isinstance(value, list):
                            col_type = "array"
                        break

            columns.append({
                "name": key,
                "type": col_type,
                "nullable": True,
            })

    # Create a "table" representing this API endpoint
    # Use a more descriptive name based on URL path
    import re
    from urllib.parse import urlparse

    # Extract a meaningful name from the URL
    parsed_url = urlparse(url)
    path_parts = [p for p in parsed_url.path.split('/') if p and p != 'api']
    suggested_name = path_parts[-1] if path_parts else data_path or "api_data"

    # Clean the name to be a valid table name
    suggested_name = re.sub(r'[^a-zA-Z0-9_]', '_', suggested_name).lower()

    table_info = TableInfo(
        schema="api",
        table=suggested_name,  # Use extracted name instead of data_path
        row_count=len(records),
        columns=columns,
        primary_keys=[],
        has_updated_at=False,
    )

    return SchemaDiscoveryResponse(
        databases=["REST API"],
        schemas=["api"],
        tables=[table_info],
    )


async def _preview_rest_api_table(
    config: Dict[str, Any],
    schema: str,
    table: str,
    limit: int,
) -> TablePreviewResponse:
    """Preview REST API data."""
    import httpx

    url = config.get("url")

    # Prepare headers
    headers = {}
    if config.get("auth_type") == "bearer":
        token = config.get("auth_token")
        if token:
            headers["Authorization"] = f"Bearer {token}"
    elif config.get("auth_type") == "api_key":
        key_name = config.get("auth_key_name", "X-API-Key")
        key_value = config.get("auth_key_value")
        if key_value:
            headers[key_name] = key_value

    # Make request
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

    # Find the data array using the table name (which is the data_path)
    records = []
    if table == "$":
        # Data is at root level
        if isinstance(data, list):
            records = data[:limit]
        else:
            records = [data]
    else:
        # Data is nested under a key
        if table in data and isinstance(data[table], list):
            records = data[table][:limit]

    # Extract columns and rows
    columns = []
    rows_data = []

    if records:
        # Get all unique keys from records
        all_keys = set()
        for record in records:
            if isinstance(record, dict):
                all_keys.update(record.keys())

        columns = sorted(all_keys)

        # Convert records to rows
        for record in records:
            if isinstance(record, dict):
                row = []
                for col in columns:
                    value = record.get(col)
                    # Convert complex types to strings for display
                    if isinstance(value, (dict, list)):
                        value = str(value)
                    row.append(value)
                rows_data.append(row)

    total_rows = len(records)

    return TablePreviewResponse(
        columns=columns,
        rows=rows_data,
        total_rows=total_rows,
    )
