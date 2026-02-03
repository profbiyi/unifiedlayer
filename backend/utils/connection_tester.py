"""
Connection Testing Utilities.

Test connections to various data sources before saving.
"""

import logging
from typing import Dict, Any, Tuple
import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)


def test_postgres_connection(config: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Test PostgreSQL connection.

    Args:
        config: Source configuration

    Returns:
        (success: bool, message: str)
    """
    try:
        import psycopg2

        conn = psycopg2.connect(
            host=config.get("host"),
            port=config.get("port", 5432),
            database=config.get("database"),
            user=config.get("username"),
            password=config.get("password"),
            connect_timeout=5,
        )

        # Test simple query
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        cursor.close()
        conn.close()

        if result and result[0] == 1:
            return True, "Connection successful"
        else:
            return False, "Connection established but test query failed"

    except Exception as e:
        logger.error(f"PostgreSQL connection test failed: {str(e)}")
        return False, f"Connection failed: {str(e)}"


def test_mysql_connection(config: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Test MySQL connection.

    Args:
        config: Source configuration

    Returns:
        (success: bool, message: str)
    """
    try:
        import pymysql

        conn = pymysql.connect(
            host=config.get("host"),
            port=config.get("port", 3306),
            database=config.get("database"),
            user=config.get("username"),
            password=config.get("password"),
            connect_timeout=5,
        )

        # Test simple query
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        cursor.close()
        conn.close()

        if result and result[0] == 1:
            return True, "Connection successful"
        else:
            return False, "Connection established but test query failed"

    except Exception as e:
        logger.error(f"MySQL connection test failed: {str(e)}")
        return False, f"Connection failed: {str(e)}"


def test_mongodb_connection(config: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Test MongoDB connection.

    Args:
        config: Source configuration

    Returns:
        (success: bool, message: str)
    """
    try:
        from pymongo import MongoClient

        connection_string = config.get("connection_string")

        client = MongoClient(
            connection_string,
            serverSelectionTimeoutMS=5000,
        )

        # Ping the server
        client.admin.command('ping')
        client.close()

        return True, "Connection successful"

    except Exception as e:
        logger.error(f"MongoDB connection test failed: {str(e)}")
        return False, f"Connection failed: {str(e)}"


def test_rest_api_connection(config: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Test REST API connection.

    Args:
        config: Source configuration

    Returns:
        (success: bool, message: str)
    """
    try:
        base_url = config.get("base_url")
        auth_type = config.get("auth_type", "none")
        headers = config.get("headers", {})

        # Prepare authentication
        auth = None
        if auth_type == "basic":
            auth = HTTPBasicAuth(
                config.get("username"),
                config.get("password")
            )
        elif auth_type == "bearer":
            headers["Authorization"] = f"Bearer {config.get('token')}"
        elif auth_type == "api_key":
            key_name = config.get("api_key_name", "X-API-Key")
            headers[key_name] = config.get("api_key")

        # Make test request
        response = requests.get(
            base_url,
            headers=headers,
            auth=auth,
            timeout=5,
        )

        if response.status_code < 400:
            return True, f"Connection successful (HTTP {response.status_code})"
        else:
            return False, f"Connection failed with HTTP {response.status_code}: {response.text[:100]}"

    except Exception as e:
        logger.error(f"REST API connection test failed: {str(e)}")
        return False, f"Connection failed: {str(e)}"


def test_mpesa_connection(config: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Test M-Pesa API connection.

    Args:
        config: Source configuration

    Returns:
        (success: bool, message: str)
    """
    try:
        # M-Pesa requires OAuth token generation first
        consumer_key = config.get("consumer_key")
        consumer_secret = config.get("consumer_secret")
        environment = config.get("environment", "sandbox")

        # Determine base URL
        if environment == "production":
            base_url = "https://api.safaricom.co.ke"
        else:
            base_url = "https://sandbox.safaricom.co.ke"

        # Test OAuth endpoint
        auth_url = f"{base_url}/oauth/v1/generate?grant_type=client_credentials"

        response = requests.get(
            auth_url,
            auth=HTTPBasicAuth(consumer_key, consumer_secret),
            timeout=5,
        )

        if response.status_code == 200:
            data = response.json()
            if "access_token" in data:
                return True, "Connection successful - OAuth token generated"
            else:
                return False, "OAuth response missing access_token"
        else:
            return False, f"OAuth failed with HTTP {response.status_code}: {response.text[:100]}"

    except Exception as e:
        logger.error(f"M-Pesa connection test failed: {str(e)}")
        return False, f"Connection failed: {str(e)}"


def test_whatsapp_connection(config: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Test WhatsApp Business API connection.

    Args:
        config: Source configuration

    Returns:
        (success: bool, message: str)
    """
    try:
        access_token = config.get("access_token")
        phone_number_id = config.get("phone_number_id")

        # Test by fetching phone number info
        url = f"https://graph.facebook.com/v17.0/{phone_number_id}"
        headers = {
            "Authorization": f"Bearer {access_token}"
        }

        response = requests.get(url, headers=headers, timeout=5)

        if response.status_code == 200:
            return True, "Connection successful - Phone number verified"
        else:
            return False, f"Connection failed with HTTP {response.status_code}: {response.text[:100]}"

    except Exception as e:
        logger.error(f"WhatsApp connection test failed: {str(e)}")
        return False, f"Connection failed: {str(e)}"


def test_s3_connection(config: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Test S3 connection.

    Args:
        config: Source/Destination configuration

    Returns:
        (success: bool, message: str)
    """
    try:
        import boto3
        from botocore.exceptions import ClientError

        s3_client = boto3.client(
            's3',
            aws_access_key_id=config.get("access_key_id") or config.get("aws_access_key_id"),
            aws_secret_access_key=config.get("secret_access_key") or config.get("aws_secret_access_key"),
            region_name=config.get("region", "us-east-1"),
        )

        # Support both bucket_name (source format) and bucket_url (destination format)
        bucket_name = config.get("bucket_name")
        if not bucket_name:
            bucket_url = config.get("bucket_url", "")
            if bucket_url.startswith("s3://"):
                bucket_name = bucket_url.replace("s3://", "").split("/")[0]

        if not bucket_name:
            return False, "Missing 'bucket_name' or 'bucket_url' in configuration"

        # Test by checking if bucket exists and is accessible
        s3_client.head_bucket(Bucket=bucket_name)

        return True, f"Connection successful - Bucket '{bucket_name}' accessible"

    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404':
            return False, f"Bucket '{bucket_name}' does not exist"
        elif error_code == '403':
            return False, f"Access denied to bucket '{bucket_name}'"
        else:
            return False, f"Connection failed: {str(e)}"
    except Exception as e:
        logger.error(f"S3 connection test failed: {str(e)}")
        return False, f"Connection failed: {str(e)}"


def test_snowflake_connection(config: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Test Snowflake connection.

    Args:
        config: Destination configuration

    Returns:
        (success: bool, message: str)
    """
    try:
        import snowflake.connector

        # Get account identifier
        host = config.get("host") or config.get("account")
        if not host:
            return False, "Missing 'host' or 'account' in configuration"

        # Strip .snowflakecomputing.com if present
        if host.endswith(".snowflakecomputing.com"):
            host = host.replace(".snowflakecomputing.com", "")

        conn = snowflake.connector.connect(
            account=host,
            user=config.get("username") or config.get("user"),
            password=config.get("password"),
            warehouse=config.get("warehouse"),
            database=config.get("database"),
            role=config.get("role"),
            login_timeout=10,
        )

        # Test simple query
        cursor = conn.cursor()
        cursor.execute("SELECT CURRENT_VERSION()")
        result = cursor.fetchone()
        cursor.close()
        conn.close()

        if result:
            return True, f"Connection successful (Snowflake version: {result[0]})"
        else:
            return False, "Connection established but test query failed"

    except Exception as e:
        logger.error(f"Snowflake connection test failed: {str(e)}")
        return False, f"Connection failed: {str(e)}"


def test_bigquery_connection(config: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Test BigQuery connection.

    Args:
        config: Destination configuration

    Returns:
        (success: bool, message: str)
    """
    try:
        from google.cloud import bigquery
        from google.oauth2 import service_account
        import json

        credentials_json = config.get("credentials_json")
        if not credentials_json:
            return False, "Missing 'credentials_json' in configuration"

        # Parse credentials if string
        if isinstance(credentials_json, str):
            credentials_json = json.loads(credentials_json)

        credentials = service_account.Credentials.from_service_account_info(
            credentials_json
        )

        client = bigquery.Client(credentials=credentials, project=credentials_json.get("project_id"))

        # Test by listing datasets (limited to 1)
        datasets = list(client.list_datasets(max_results=1))

        return True, f"Connection successful (Project: {client.project})"

    except Exception as e:
        logger.error(f"BigQuery connection test failed: {str(e)}")
        return False, f"Connection failed: {str(e)}"


def test_gcs_connection(config: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Test Google Cloud Storage connection.

    Args:
        config: Destination configuration

    Returns:
        (success: bool, message: str)
    """
    try:
        from google.cloud import storage
        from google.oauth2 import service_account
        import json

        bucket_url = config.get("bucket_url", "")
        if not bucket_url.startswith("gs://"):
            return False, "bucket_url must start with 'gs://'"

        # Extract bucket name from URL
        bucket_name = bucket_url.replace("gs://", "").split("/")[0]

        credentials_json = config.get("service_account_json")
        if credentials_json:
            if isinstance(credentials_json, str):
                credentials_json = json.loads(credentials_json)
            credentials = service_account.Credentials.from_service_account_info(credentials_json)
            client = storage.Client(credentials=credentials)
        else:
            # Use application default credentials
            client = storage.Client()

        # Test bucket access
        bucket = client.bucket(bucket_name)
        bucket.reload()

        return True, f"Connection successful - Bucket '{bucket_name}' accessible"

    except Exception as e:
        logger.error(f"GCS connection test failed: {str(e)}")
        return False, f"Connection failed: {str(e)}"


def test_azure_blob_connection(config: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Test Azure Blob Storage connection.

    Args:
        config: Destination configuration

    Returns:
        (success: bool, message: str)
    """
    try:
        from azure.storage.blob import BlobServiceClient

        bucket_url = config.get("bucket_url", "")
        account_name = config.get("account_name")
        account_key = config.get("account_key")

        if not account_name or not account_key:
            return False, "Missing 'account_name' or 'account_key' in configuration"

        # Extract container name from URL
        # Format: az://container or abfs://container@account.dfs.core.windows.net
        if bucket_url.startswith("az://"):
            container_name = bucket_url.replace("az://", "").split("/")[0]
        elif bucket_url.startswith("abfs://"):
            container_name = bucket_url.replace("abfs://", "").split("@")[0]
        else:
            return False, "bucket_url must start with 'az://' or 'abfs://'"

        # Create connection string
        connection_string = (
            f"DefaultEndpointsProtocol=https;"
            f"AccountName={account_name};"
            f"AccountKey={account_key};"
            f"EndpointSuffix=core.windows.net"
        )

        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service_client.get_container_client(container_name)

        # Test container access
        container_client.get_container_properties()

        return True, f"Connection successful - Container '{container_name}' accessible"

    except Exception as e:
        logger.error(f"Azure Blob connection test failed: {str(e)}")
        return False, f"Connection failed: {str(e)}"


def test_duckdb_connection(config: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Test DuckDB connection.

    Args:
        config: Destination configuration

    Returns:
        (success: bool, message: str)
    """
    try:
        import duckdb

        database_path = config.get("database_path", ":memory:")

        # Try to connect
        conn = duckdb.connect(database_path)

        # Test simple query
        result = conn.execute("SELECT 1").fetchone()
        conn.close()

        if result and result[0] == 1:
            return True, f"Connection successful (DuckDB at {database_path})"
        else:
            return False, "Connection established but test query failed"

    except Exception as e:
        logger.error(f"DuckDB connection test failed: {str(e)}")
        return False, f"Connection failed: {str(e)}"


def test_redshift_connection(config: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Test Amazon Redshift connection.

    Args:
        config: Destination configuration

    Returns:
        (success: bool, message: str)
    """
    try:
        import psycopg2

        conn = psycopg2.connect(
            host=config.get("host"),
            port=config.get("port", 5439),  # Redshift default port
            database=config.get("database"),
            user=config.get("username") or config.get("user"),
            password=config.get("password"),
            connect_timeout=10,
        )

        # Test simple query
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        cursor.close()
        conn.close()

        if result and result[0] == 1:
            return True, "Connection successful"
        else:
            return False, "Connection established but test query failed"

    except Exception as e:
        logger.error(f"Redshift connection test failed: {str(e)}")
        return False, f"Connection failed: {str(e)}"


def test_connection(source_type: str, config: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Test connection for any source type.

    Args:
        source_type: Type of data source
        config: Source configuration

    Returns:
        (success: bool, message: str)
    """
    logger.info(f"Testing connection for source type: {source_type}")

    # Map source type to test function
    testers = {
        "postgres": test_postgres_connection,
        "mysql": test_mysql_connection,
        "mongodb": test_mongodb_connection,
        "rest_api": test_rest_api_connection,
        "mpesa": test_mpesa_connection,
        "whatsapp_business": test_whatsapp_connection,
        "s3": test_s3_connection,
    }

    tester = testers.get(source_type.lower())

    if not tester:
        logger.warning(f"No connection tester available for source type: {source_type}")
        return True, f"Connection test not implemented for {source_type} (skipped)"

    try:
        return tester(config)
    except Exception as e:
        logger.error(f"Unexpected error testing {source_type} connection: {str(e)}", exc_info=True)
        return False, f"Unexpected error: {str(e)}"


def test_destination_connection(destination_type: str, config: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Test connection for any destination type.

    Args:
        destination_type: Type of destination
        config: Destination configuration

    Returns:
        (success: bool, message: str)
    """
    logger.info(f"Testing connection for destination type: {destination_type}")

    # Map destination type to test function
    testers = {
        "postgres": test_postgres_connection,
        "mysql": test_mysql_connection,
        "snowflake": test_snowflake_connection,
        "bigquery": test_bigquery_connection,
        "s3": test_s3_connection,
        "gcs": test_gcs_connection,
        "azure_blob": test_azure_blob_connection,
        "duckdb": test_duckdb_connection,
        "redshift": test_redshift_connection,
    }

    tester = testers.get(destination_type.lower())

    if not tester:
        logger.warning(f"No connection tester available for destination type: {destination_type}")
        return True, f"Connection test not implemented for {destination_type} (skipped)"

    try:
        return tester(config)
    except Exception as e:
        logger.error(f"Unexpected error testing {destination_type} connection: {str(e)}", exc_info=True)
        return False, f"Unexpected error: {str(e)}"
