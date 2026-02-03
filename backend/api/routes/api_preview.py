"""
API Source Preview Endpoints.

Enhanced endpoints for previewing API data with full pagination support.
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
import logging

from backend.database import get_db
from backend.models.pipeline import User
from backend.auth import get_current_user
from backend.connectors.rest_api import RESTAPIConnector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api-preview", tags=["API Preview"])


class APIPreviewRequest(BaseModel):
    """Request to preview API data with pagination."""
    base_url: str
    endpoint_path: str
    endpoint_name: Optional[str] = None  # Custom table name
    data_path: Optional[str] = None

    # Authentication
    auth_type: str = "none"
    auth_config: Optional[Dict[str, Any]] = None

    # Pagination
    pagination_type: str = "none"
    pagination_config: Optional[Dict[str, Any]] = None

    # Preview options
    max_pages: int = 5  # Limit pages for preview
    max_records: int = 100  # Max records to return

    # Output format
    format: str = "table"  # "table" or "json"


class APIPreviewResponse(BaseModel):
    """Response from API preview."""
    success: bool
    endpoint_name: str
    total_records: int
    total_pages_fetched: int
    pagination_info: Dict[str, Any]

    # Table format
    columns: Optional[List[str]] = None
    rows: Optional[List[List[Any]]] = None

    # JSON format
    data: Optional[List[Dict[str, Any]]] = None

    # Metadata
    sample_record: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@router.post("/preview", response_model=APIPreviewResponse)
async def preview_api_source(
    request: APIPreviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Preview API data with full pagination support.

    Features:
    - Fetches multiple pages (up to max_pages)
    - Supports all pagination strategies
    - Returns data in table or JSON format
    - Provides pagination metadata
    """
    logger.info(f"Previewing API: {request.base_url}{request.endpoint_path}")

    try:
        # Create connector with pagination config
        connector = RESTAPIConnector(
            base_url=request.base_url,
            auth_type=request.auth_type,
            auth_config=request.auth_config or {},
            pagination_type=request.pagination_type,
            pagination_config=request.pagination_config or {},
        )

        # Fetch data with pagination
        records = []
        pages_fetched = 0

        for record in connector.fetch_data(
            endpoint=request.endpoint_path,
            data_path=request.data_path,
        ):
            records.append(record)

            # Check if we've hit the record limit
            if len(records) >= request.max_records:
                logger.info(f"Reached max_records limit: {request.max_records}")
                break

            # Estimate pages (assuming consistent page size)
            if request.pagination_config:
                page_size = request.pagination_config.get('page_size') or \
                           request.pagination_config.get('limit') or 20
                estimated_pages = len(records) // page_size + 1
                if estimated_pages >= request.max_pages:
                    logger.info(f"Reached max_pages limit: {request.max_pages}")
                    break

        if not records:
            return APIPreviewResponse(
                success=False,
                endpoint_name=request.endpoint_name or "api_data",
                total_records=0,
                total_pages_fetched=0,
                pagination_info={
                    "pagination_type": request.pagination_type,
                    "note": "No records found"
                },
                error="No records found in API response"
            )

        # Calculate pages fetched
        if request.pagination_config:
            page_size = request.pagination_config.get('page_size') or \
                       request.pagination_config.get('limit') or 20
            pages_fetched = (len(records) // page_size) + (1 if len(records) % page_size > 0 else 0)
        else:
            pages_fetched = 1

        # Get column names from first record
        sample_record = records[0]
        columns = sorted(sample_record.keys()) if isinstance(sample_record, dict) else []

        # Remove internal dlt columns for cleaner preview
        display_columns = [col for col in columns if not col.startswith('_dlt_')]

        # Format response based on requested format
        if request.format == "json":
            # Return as JSON array
            clean_data = []
            for record in records:
                if isinstance(record, dict):
                    # Remove internal columns
                    clean_record = {k: v for k, v in record.items() if not k.startswith('_dlt_')}
                    clean_data.append(clean_record)
                else:
                    clean_data.append(record)

            return APIPreviewResponse(
                success=True,
                endpoint_name=request.endpoint_name or "api_data",
                total_records=len(records),
                total_pages_fetched=pages_fetched,
                pagination_info={
                    "pagination_type": request.pagination_type,
                    "pages_fetched": pages_fetched,
                    "max_pages": request.max_pages,
                    "max_records_reached": len(records) >= request.max_records
                },
                data=clean_data,
                sample_record={k: v for k, v in sample_record.items() if not k.startswith('_dlt_')}
            )
        else:
            # Return in table format
            rows = []
            for record in records:
                if isinstance(record, dict):
                    row = []
                    for col in display_columns:
                        value = record.get(col)
                        # Convert complex types to strings
                        if isinstance(value, (dict, list)):
                            value = str(value)
                        row.append(value)
                    rows.append(row)

            return APIPreviewResponse(
                success=True,
                endpoint_name=request.endpoint_name or "api_data",
                total_records=len(records),
                total_pages_fetched=pages_fetched,
                pagination_info={
                    "pagination_type": request.pagination_type,
                    "pages_fetched": pages_fetched,
                    "max_pages": request.max_pages,
                    "max_records_reached": len(records) >= request.max_records
                },
                columns=display_columns,
                rows=rows,
                sample_record={k: v for k, v in sample_record.items() if not k.startswith('_dlt_')}
            )

    except Exception as e:
        logger.error(f"API preview failed: {str(e)}", exc_info=True)
        return APIPreviewResponse(
            success=False,
            endpoint_name=request.endpoint_name or "api_data",
            total_records=0,
            total_pages_fetched=0,
            pagination_info={
                "pagination_type": request.pagination_type,
            },
            error=str(e)
        )


class QuickTestRequest(BaseModel):
    """Quick test of API endpoint to detect pagination."""
    url: str
    auth_type: str = "none"
    auth_config: Optional[Dict[str, Any]] = None


class QuickTestResponse(BaseModel):
    """Quick test response with auto-detected configuration."""
    success: bool
    status_code: Optional[int] = None
    data_path: Optional[str] = None
    record_count: int = 0
    total_count: Optional[int] = None

    # Auto-detected pagination
    detected_pagination_type: Optional[str] = None
    suggested_pagination_config: Optional[Dict[str, Any]] = None

    # Sample data
    sample_record: Optional[Dict[str, Any]] = None
    columns: List[str] = []

    error: Optional[str] = None


@router.post("/quick-test", response_model=QuickTestResponse)
async def quick_test_api(
    request: QuickTestRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Quick test of API endpoint with auto-detection of pagination.

    Analyzes the response to detect:
    - Data path
    - Pagination strategy
    - Total record count
    - Sample data structure
    """
    logger.info(f"Quick testing API: {request.url}")

    try:
        import httpx
        from urllib.parse import urlparse

        # Parse URL to separate base and path
        parsed = urlparse(request.url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        endpoint_path = parsed.path
        if parsed.query:
            endpoint_path += f"?{parsed.query}"

        # Prepare headers
        headers = {}
        if request.auth_type == "bearer":
            token = request.auth_config.get("token") if request.auth_config else None
            if token:
                headers["Authorization"] = f"Bearer {token}"
        elif request.auth_type == "api_key":
            key_name = request.auth_config.get("header_name", "X-API-Key") if request.auth_config else "X-API-Key"
            key_value = request.auth_config.get("api_key") if request.auth_config else None
            if key_value:
                headers[key_name] = key_value

        # Make request
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(request.url, headers=headers)
            response.raise_for_status()

            response_headers = dict(response.headers)
            data = response.json()

        # Analyze response structure
        records = []
        data_path = None
        total_count = None
        detected_pagination = None
        suggested_config = {}

        if isinstance(data, list):
            # Data is array at root
            records = data
            data_path = "$"
            detected_pagination = "none"
        elif isinstance(data, dict):
            # Look for data arrays
            for key in ["results", "data", "items", "records", "rows"]:
                if key in data and isinstance(data[key], list):
                    records = data[key]
                    data_path = key
                    break

            # Detect pagination type
            # 1. Check for next URL in response
            if "next" in data and data["next"]:
                detected_pagination = "next_url"
                suggested_config = {"next_url_path": "next"}

            # 2. Check for page info
            elif "info" in data and isinstance(data["info"], dict):
                info = data["info"]
                if "next" in info and info["next"]:
                    detected_pagination = "next_url"
                    suggested_config = {"next_url_path": "info.next"}
                elif "pages" in info:
                    detected_pagination = "page"
                    suggested_config = {
                        "page_param": "page",
                        "size_param": "per_page",
                        "page_size": len(records) if records else 20
                    }
                if "count" in info:
                    total_count = info["count"]

            # 3. Check for pagination/paging object
            elif any(k in data for k in ["pagination", "paging", "page_info"]):
                pag_key = next(k for k in ["pagination", "paging", "page_info"] if k in data)
                pag_obj = data[pag_key]

                if isinstance(pag_obj, dict):
                    if "next_cursor" in pag_obj or "next" in pag_obj:
                        detected_pagination = "cursor"
                        cursor_key = "next_cursor" if "next_cursor" in pag_obj else "next"
                        suggested_config = {
                            "cursor_path": f"{pag_key}.{cursor_key}",
                            "cursor_param": "cursor"
                        }
                    elif "next_page_token" in pag_obj or "nextPageToken" in pag_obj:
                        detected_pagination = "token"
                        token_key = "next_page_token" if "next_page_token" in pag_obj else "nextPageToken"
                        suggested_config = {
                            "token_path": f"{pag_key}.{token_key}",
                            "token_param": "page_token"
                        }

                    if "total" in pag_obj:
                        total_count = pag_obj["total"]

            # 4. Check Link header
            if "Link" in response_headers or "link" in response_headers:
                link_header = response_headers.get("Link") or response_headers.get("link")
                if 'rel="next"' in link_header or "rel='next'" in link_header:
                    detected_pagination = "link_header"
                    suggested_config = {}

        # Get sample record and columns
        sample_record = None
        columns = []

        if records:
            sample_record = records[0] if records else None
            if isinstance(sample_record, dict):
                columns = sorted(sample_record.keys())

        return QuickTestResponse(
            success=True,
            status_code=response.status_code,
            data_path=data_path,
            record_count=len(records),
            total_count=total_count,
            detected_pagination_type=detected_pagination,
            suggested_pagination_config=suggested_config if suggested_config else None,
            sample_record=sample_record,
            columns=columns
        )

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error: {e}")
        return QuickTestResponse(
            success=False,
            error=f"HTTP {e.response.status_code}: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Quick test failed: {str(e)}", exc_info=True)
        return QuickTestResponse(
            success=False,
            error=str(e)
        )
