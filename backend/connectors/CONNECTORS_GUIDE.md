# Data Platform Source Connectors Guide

This guide provides comprehensive documentation for all source connectors in the data platform, with special focus on pagination strategies for API-based sources.

## Table of Contents

1. [REST API Connector](#rest-api-connector)
2. [WhatsApp Business Connector](#whatsapp-business-connector)
3. [M-Pesa Connector](#mpesa-connector)
4. [MySQL Connector](#mysql-connector)
5. [PostgreSQL Connector](#postgresql-connector)

---

## REST API Connector

The REST API connector is a fully configurable, production-ready connector that supports any REST API with multiple authentication and pagination strategies.

### Features

- **Multiple Authentication Types**: API Key, Bearer Token, OAuth2, Basic Auth
- **7 Pagination Strategies**: PAGE, OFFSET, CURSOR, LINK_HEADER, TOKEN, NEXT_URL, NONE
- **Rate Limiting**: Configurable requests per minute
- **Retry Logic**: Exponential backoff with automatic retries
- **Flexible Configuration**: Per-endpoint customization

### Pagination Strategies

#### 1. PAGE Pagination

Used for APIs that use page numbers and page sizes.

**Example APIs**: Most paginated REST APIs, GitHub API (pages), Stripe API

**Configuration:**
```python
pagination_config = {
    "page_param": "page",           # Query parameter for page number
    "size_param": "page_size",      # Query parameter for page size
    "page_size": 100                # Number of items per page
}
```

**Example:**
```python
from backend.connectors.rest_api import RESTAPIConnector

connector = RESTAPIConnector(
    base_url="https://api.example.com",
    pagination_type="page",
    pagination_config={
        "page_param": "page",
        "size_param": "per_page",
        "page_size": 50
    }
)

# Fetches: /users?page=1&per_page=50
#          /users?page=2&per_page=50
#          ... until empty page
data = list(connector.fetch_data("/users"))
```

#### 2. OFFSET Pagination

Used for APIs that use offset and limit parameters.

**Example APIs**: PostgreSQL-style APIs, many database-backed APIs

**Configuration:**
```python
pagination_config = {
    "offset_param": "offset",       # Query parameter for offset
    "limit_param": "limit",         # Query parameter for limit
    "limit": 100                    # Number of items per request
}
```

**Example:**
```python
connector = RESTAPIConnector(
    base_url="https://api.example.com",
    pagination_type="offset",
    pagination_config={
        "offset_param": "skip",
        "limit_param": "take",
        "limit": 100
    }
)

# Fetches: /products?skip=0&take=100
#          /products?skip=100&take=100
#          ... until less than limit returned
data = list(connector.fetch_data("/products"))
```

#### 3. CURSOR Pagination

Used for APIs that return a cursor/token pointing to the next page in the response body.

**Example APIs**: Twitter API, Facebook Graph API, Slack API

**Configuration:**
```python
pagination_config = {
    "cursor_path": "next_cursor",   # JSON path to cursor in response
    "cursor_param": "cursor"        # Query parameter for cursor
}
```

**Example:**
```python
connector = RESTAPIConnector(
    base_url="https://api.example.com",
    pagination_type="cursor",
    pagination_config={
        "cursor_path": "pagination.next_cursor",  # Nested path
        "cursor_param": "cursor"
    }
)

# Response: {"data": [...], "pagination": {"next_cursor": "abc123"}}
# Fetches: /items?cursor=abc123
data = list(connector.fetch_data("/items"))
```

#### 4. LINK_HEADER Pagination

Used for APIs that follow RFC 5988 and provide pagination links in HTTP headers.

**Example APIs**: GitHub API, GitLab API

**Configuration:**
```python
# No configuration needed - reads from Link header
pagination_type = "link_header"
```

**Example:**
```python
connector = RESTAPIConnector(
    base_url="https://api.github.com",
    pagination_type="link_header",
    headers={"User-Agent": "MyApp"}
)

# Reads Link header: <https://api.github.com/users?page=2>; rel="next"
data = list(connector.fetch_data("/users", params={"per_page": 100}))
```

#### 5. TOKEN Pagination

Used for APIs that return a next_page_token or similar token in the response body.

**Example APIs**: Google APIs, YouTube API, Google Drive API

**Configuration:**
```python
pagination_config = {
    "token_path": "next_page_token",    # JSON path to token in response
    "token_param": "page_token"         # Query parameter for token
}
```

**Example:**
```python
connector = RESTAPIConnector(
    base_url="https://api.example.com",
    pagination_type="token",
    pagination_config={
        "token_path": "nextPageToken",
        "token_param": "pageToken"
    }
)

# Response: {"items": [...], "nextPageToken": "xyz789"}
# Fetches: /videos?pageToken=xyz789
data = list(connector.fetch_data("/videos"))
```

#### 6. NEXT_URL Pagination

Used for APIs that return the full URL to the next page in the response body.

**Example APIs**: Many REST APIs, especially those following HATEOAS

**Configuration:**
```python
pagination_config = {
    "next_url_path": "next"    # JSON path to next URL
}
```

**Example:**
```python
connector = RESTAPIConnector(
    base_url="https://api.example.com",
    pagination_type="next_url",
    pagination_config={
        "next_url_path": "links.next"  # Nested path
    }
)

# Response: {"data": [...], "links": {"next": "https://api.example.com/data?page=2"}}
data = list(connector.fetch_data("/data"))
```

#### 7. NONE (No Pagination)

For APIs that return all data in a single request or for testing.

**Configuration:**
```python
pagination_type = "none"
```

**Example:**
```python
connector = RESTAPIConnector(
    base_url="https://api.example.com",
    pagination_type="none"
)

# Single request, no pagination
data = list(connector.fetch_data("/config"))
```

### Authentication Examples

#### API Key Authentication

```python
connector = RESTAPIConnector(
    base_url="https://api.example.com",
    auth_type="api_key",
    auth_config={
        "api_key": "your-api-key-here",
        "header_name": "X-API-Key"  # Default if not specified
    }
)
```

#### Bearer Token Authentication

```python
connector = RESTAPIConnector(
    base_url="https://api.example.com",
    auth_type="bearer",
    auth_config={
        "token": "your-bearer-token"
    }
)
```

#### OAuth2 Authentication

```python
connector = RESTAPIConnector(
    base_url="https://api.example.com",
    auth_type="oauth2",
    auth_config={
        "token_url": "https://auth.example.com/oauth/token",
        "client_id": "your-client-id",
        "client_secret": "your-client-secret",
        "scope": "read write"
    }
)
```

#### Basic Authentication

```python
connector = RESTAPIConnector(
    base_url="https://api.example.com",
    auth_type="basic",
    auth_config={
        "username": "your-username",
        "password": "your-password"
    }
)
```

### Complete Example with dlt

```python
import dlt
from backend.connectors.rest_api import rest_api_source

# Define endpoints
endpoints = [
    {
        "name": "users",
        "path": "/api/users",
        "data_path": "data",
        "primary_key": "id",
        "write_disposition": "merge"
    },
    {
        "name": "orders",
        "path": "/api/orders",
        "data_path": "results",
        "primary_key": "order_id",
        "write_disposition": "append"
    }
]

# Create pipeline
pipeline = dlt.pipeline(
    pipeline_name="api_pipeline",
    destination="postgres",
    dataset_name="my_data"
)

# Run pipeline
load_info = pipeline.run(
    rest_api_source(
        base_url="https://api.example.com",
        endpoints=endpoints,
        auth_type="bearer",
        auth_config={"token": "your-token"},
        pagination_type="cursor",
        pagination_config={
            "cursor_path": "next_cursor",
            "cursor_param": "cursor"
        },
        rate_limit=60  # Max 60 requests per minute
    )
)
```

### Using with Data Platform API

```json
POST /api/sources

{
  "name": "My API Source",
  "source_type": "rest_api",
  "organization_id": 1,
  "config": {
    "base_url": "https://api.example.com",
    "endpoints": [
      {
        "name": "users",
        "path": "/users",
        "data_path": "data",
        "primary_key": "id"
      }
    ],
    "auth_type": "bearer",
    "auth_config": {
      "token": "your-token"
    },
    "pagination_type": "page",
    "pagination_config": {
      "page_size": 100
    }
  }
}
```

---

## WhatsApp Business Connector

Production-ready connector for WhatsApp Business API with cursor-based pagination.

### Features

- Message fetching with automatic pagination
- Template management
- Analytics and conversation data
- Webhook event handling
- Signature verification

### Pagination

WhatsApp Business API uses **cursor-based pagination** automatically handled by the connector.

### Example Usage

```python
from backend.connectors.whatsapp_business import whatsapp_business_source
import dlt

pipeline = dlt.pipeline(
    pipeline_name="whatsapp_pipeline",
    destination="postgres",
    dataset_name="whatsapp_data"
)

load_info = pipeline.run(
    whatsapp_business_source(
        access_token="your-access-token",
        phone_number_id="your-phone-number-id",
        business_account_id="your-business-account-id"
    )
)
```

### Resources

- **messages**: All WhatsApp messages (incremental)
- **templates**: Message templates (full refresh)
- **analytics**: Analytics data (incremental)
- **conversations**: Conversation analytics (incremental)

---

## M-Pesa Connector

Production-ready connector for Safaricom M-Pesa API with OAuth2 authentication.

### Features

- OAuth2 token auto-refresh
- Transaction fetching with page-based pagination
- Rate limiting (100 req/min)
- Incremental loading
- Sandbox and production environments

### Pagination

M-Pesa API uses **page-based pagination** with `page` and `page_size` parameters.

### Example Usage

```python
from backend.connectors.mpesa import mpesa_source
import dlt

pipeline = dlt.pipeline(
    pipeline_name="mpesa_pipeline",
    destination="postgres",
    dataset_name="mpesa_data"
)

load_info = pipeline.run(
    mpesa_source(
        consumer_key="your-consumer-key",
        consumer_secret="your-consumer-secret",
        environment="sandbox",  # or "production"
        shortcode="your-shortcode"
    )
)
```

### Resources

- **transactions**: M-Pesa transactions (incremental by date)
- **balance**: Current account balance (snapshot)

---

## MySQL Connector

Production-ready MySQL connector with CDC support via binlog.

### Features

- Automatic schema detection
- Connection pooling
- Incremental loading by timestamp
- Binlog CDC support
- Batch processing

### Pagination

MySQL connector uses **batch fetching** with configurable `batch_size` (default: 1000 rows per batch).

For incremental loading, it tracks the last value of a cursor column (timestamp or ID).

### Example Usage

```python
from backend.connectors.mysql import mysql_source
import dlt

pipeline = dlt.pipeline(
    pipeline_name="mysql_pipeline",
    destination="postgres",
    dataset_name="mysql_data"
)

load_info = pipeline.run(
    mysql_source(
        host="localhost",
        port=3306,
        database="mydb",
        user="root",
        password="password",
        tables=["users", "orders"],  # None = all tables
        enable_cdc=False  # Set to True for binlog CDC
    )
)
```

### CDC (Change Data Capture)

Enable CDC to track all database changes via MySQL binlog:

```python
load_info = pipeline.run(
    mysql_source(
        host="localhost",
        database="mydb",
        user="root",
        password="password",
        enable_cdc=True  # Enables binlog event tracking
    )
)
```

---

## PostgreSQL Connector

Production-ready PostgreSQL connector with CDC support.

### Features

- Automatic schema detection
- Connection pooling
- Incremental loading by timestamp/ID
- Batch processing
- WAL-based CDC support

### Pagination

PostgreSQL connector uses **batch fetching** with configurable `batch_size` (default: 1000 rows per batch).

Supports incremental loading via cursor columns (timestamp or ID fields).

### Example Usage

```python
from backend.connectors.postgres import postgres_source
import dlt

pipeline = dlt.pipeline(
    pipeline_name="postgres_pipeline",
    destination="bigquery",
    dataset_name="postgres_data"
)

load_info = pipeline.run(
    postgres_source(
        host="localhost",
        port=5432,
        database="mydb",
        user="postgres",
        password="password",
        tables=["users", "orders"]
    )
)
```

---

## Best Practices

### 1. Choose the Right Pagination Strategy

- **PAGE**: When API uses page numbers (GitHub, most REST APIs)
- **OFFSET**: When API uses SQL-style offset/limit
- **CURSOR**: For large datasets with stable cursors (Twitter, Facebook)
- **LINK_HEADER**: When API provides Link headers (GitHub, GitLab)
- **TOKEN**: For Google APIs and similar token-based systems
- **NEXT_URL**: When API provides full next page URLs
- **NONE**: For single-response endpoints or small datasets

### 2. Configure Appropriate Batch Sizes

- Start with 100-1000 items per page
- Reduce if you hit rate limits
- Increase for better performance if API allows

### 3. Use Rate Limiting

Always configure rate limits to avoid API throttling:

```python
connector = RESTAPIConnector(
    base_url="https://api.example.com",
    rate_limit=60  # 60 requests per minute
)
```

### 4. Handle Authentication Securely

- Store credentials in environment variables or secrets management
- Use OAuth2 when available for better security
- Rotate API keys regularly

### 5. Monitor and Log

All connectors include comprehensive logging. Monitor logs for:
- Rate limit warnings
- Authentication failures
- Pagination issues
- Data validation errors

### 6. Test with Small Batches First

When configuring a new source, start with small page sizes to verify:
- Pagination works correctly
- Data path extraction is accurate
- Authentication is successful

---

## Troubleshooting

### Issue: Pagination Not Working

**Solution**: Check the pagination configuration matches the API's actual parameters:

```python
# Verify parameter names in API documentation
# Common variations:
# - page / pageNumber / pageNum
# - page_size / pageSize / perPage / limit
# - cursor / next_cursor / continuation_token
```

### Issue: Rate Limit Errors

**Solution**: Configure appropriate rate limiting:

```python
connector = RESTAPIConnector(
    base_url="https://api.example.com",
    rate_limit=30  # Reduce to match API limits
)
```

### Issue: Empty Data

**Solution**: Check the `data_path` configuration:

```python
# For response: {"result": {"items": [...]}}
data_path = "result.items"

# For response: {"data": [...]}
data_path = "data"

# For response: [...]  (array at root)
data_path = None  # Let connector auto-detect
```

### Issue: Authentication Failures

**Solution**: Verify credentials and auth type:

```python
# Check if token has expired
# Verify API key is active
# Ensure OAuth2 credentials are correct
# Check if IP is whitelisted (for some APIs)
```

---

## API Reference

### RESTAPIConnector

```python
RESTAPIConnector(
    base_url: str,                      # Base URL for the API
    auth_type: AuthType = "none",       # Authentication type
    auth_config: dict = None,           # Authentication configuration
    pagination_type: PaginationType = "none",  # Pagination strategy
    pagination_config: dict = None,     # Pagination configuration
    rate_limit: int = None,            # Max requests per minute
    headers: dict = None               # Additional headers
)
```

### Supported Auth Types

- `none`: No authentication
- `api_key`: API key in header
- `bearer`: Bearer token authentication
- `oauth2`: OAuth2 client credentials flow
- `basic`: HTTP Basic authentication

### Supported Pagination Types

- `page`: Page number + page size
- `offset`: Offset + limit
- `cursor`: Cursor-based pagination
- `link_header`: RFC 5988 Link header
- `token`: Page token (Google-style)
- `next_url`: Next URL in response body
- `none`: No pagination

---

## Version History

- **v1.2.0** (2024-01-07): Added TOKEN and NEXT_URL pagination, fixed LINK_HEADER
- **v1.1.0** (2024-01-06): Added validation and improved documentation
- **v1.0.0** (2024-01-05): Initial release with PAGE, OFFSET, CURSOR, LINK_HEADER

---

## Support

For issues or questions:
- Check the logs for detailed error messages
- Verify API documentation matches configuration
- Test with a simple example first
- Contact support with connector logs and configuration
