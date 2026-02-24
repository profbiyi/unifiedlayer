"""
CSV File Connector.

Reads data from CSV files with support for:
- File upload (base64 encoded content)
- Local file path
- URL fetch (download CSV from URL)
- Configurable delimiters, encodings, and header handling
"""
import base64
import csv
import io
import logging
import os
from datetime import datetime
from typing import Any, Dict, Iterator, List, Optional
from urllib.parse import urlparse

import requests

from backend.connectors.sdk import (
    AuthType,
    BaseConnector,
    ConnectorCapabilities,
    ConnectorMetadata,
    PaginationType,
    register_connector,
)

logger = logging.getLogger(__name__)


class CSVConnectorError(Exception):
    """Custom exception for CSV connector errors."""
    pass


# Delimiter mapping for user-friendly names
DELIMITER_MAP = {
    "comma": ",",
    "semicolon": ";",
    "tab": "\t",
    "pipe": "|",
}

# Supported encodings
SUPPORTED_ENCODINGS = [
    "utf-8",
    "utf-8-sig",  # UTF-8 with BOM
    "latin-1",
    "iso-8859-1",
    "cp1252",  # Windows Western European
    "ascii",
]

# Common content types for CSV files
CSV_CONTENT_TYPES = [
    "text/csv",
    "text/plain",
    "application/csv",
    "application/octet-stream",
]


def _infer_column_type(values: List[str]) -> str:
    """
    Infer the data type of a column based on sample values.

    Args:
        values: List of string values from the column

    Returns:
        Inferred type: 'integer', 'float', 'boolean', 'datetime', or 'string'
    """
    if not values:
        return "string"

    # Filter out empty values for type inference
    non_empty = [v.strip() for v in values if v and v.strip()]
    if not non_empty:
        return "string"

    # Check for boolean
    bool_values = {"true", "false", "yes", "no", "1", "0", "t", "f", "y", "n"}
    if all(v.lower() in bool_values for v in non_empty):
        return "boolean"

    # Check for integer
    try:
        for v in non_empty:
            # Remove commas from numbers (e.g., "1,000")
            clean = v.replace(",", "")
            int(clean)
        return "integer"
    except ValueError:
        pass

    # Check for float
    try:
        for v in non_empty:
            clean = v.replace(",", "")
            float(clean)
        return "float"
    except ValueError:
        pass

    # Check for datetime patterns
    datetime_patterns = [
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%d-%m-%Y",
        "%Y/%m/%d",
    ]
    for pattern in datetime_patterns:
        try:
            for v in non_empty[:10]:  # Check first 10 non-empty values
                datetime.strptime(v, pattern)
            return "datetime"
        except ValueError:
            continue

    return "string"


def _convert_value(value: str, inferred_type: str) -> Any:
    """
    Convert a string value to its inferred type.

    Args:
        value: String value to convert
        inferred_type: Target type

    Returns:
        Converted value or original string if conversion fails
    """
    if not value or not value.strip():
        return None

    value = value.strip()

    try:
        if inferred_type == "integer":
            return int(value.replace(",", ""))
        elif inferred_type == "float":
            return float(value.replace(",", ""))
        elif inferred_type == "boolean":
            return value.lower() in {"true", "yes", "1", "t", "y"}
        elif inferred_type == "datetime":
            # Try to parse as ISO format first
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00")).isoformat()
            except ValueError:
                pass
            # Try common patterns
            for pattern in ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"]:
                try:
                    return datetime.strptime(value, pattern).isoformat()
                except ValueError:
                    continue
            return value
        else:
            return value
    except (ValueError, TypeError):
        return value


def _sanitize_column_name(name: str) -> str:
    """
    Sanitize a column name for use as a field name.

    Args:
        name: Original column name

    Returns:
        Sanitized column name (lowercase, underscores instead of spaces)
    """
    if not name:
        return "unnamed"

    # Replace spaces and special characters with underscores
    sanitized = name.strip().lower()
    sanitized = "".join(c if c.isalnum() else "_" for c in sanitized)

    # Remove consecutive underscores
    while "__" in sanitized:
        sanitized = sanitized.replace("__", "_")

    # Remove leading/trailing underscores
    sanitized = sanitized.strip("_")

    # Ensure it doesn't start with a number
    if sanitized and sanitized[0].isdigit():
        sanitized = f"col_{sanitized}"

    return sanitized or "unnamed"


@register_connector
class CSVConnector(BaseConnector):
    """
    CSV file connector supporting file upload, local paths, and URL fetch.

    Features:
    - Base64 encoded file content
    - Local file path reading
    - URL download with streaming
    - Configurable delimiters (comma, semicolon, tab, pipe)
    - Multiple encoding support
    - Header row detection or auto-generation
    - Skip rows option for files with metadata rows
    - Automatic type inference
    """

    metadata = ConnectorMetadata(
        name="csv",
        display_name="CSV File",
        description=(
            "Import data from CSV files. Supports file upload, local file paths, "
            "and URL download. Configure delimiters, encodings, and header handling."
        ),
        icon="file-spreadsheet",
        category="file",
        version="1.0.0",
        author="UnifiedLayer",
        documentation_url="",
        capabilities=ConnectorCapabilities(
            supports_incremental=False,
            supports_cdc=False,
            supports_schema_discovery=True,
            supports_connection_test=True,
            supports_parallel_extraction=False,
            max_concurrent_tables=1,
            auth_types=[AuthType.NONE],
            pagination_type=PaginationType.NONE,
        ),
        supported_tables=["csv_data"],
    )

    def setup(self):
        """Initialize connector state."""
        self._csv_content: Optional[str] = None
        self._headers: Optional[List[str]] = None
        self._rows: Optional[List[List[str]]] = None
        self._column_types: Optional[Dict[str, str]] = None
        self._table_name: str = self.config.get("table_name", "csv_data")

    def get_config_schema(self) -> Dict[str, Any]:
        """Return the configuration schema for the CSV connector."""
        return {
            "source_type": {
                "type": "select",
                "options": ["file_upload", "file_path", "url"],
                "default": "file_upload",
                "required": True,
                "description": "How to provide the CSV data",
            },
            "file_content": {
                "type": "string",
                "required": False,
                "description": "Base64 encoded CSV file content (for file_upload source_type)",
            },
            "file_path": {
                "type": "string",
                "required": False,
                "description": "Local file path to CSV file (for file_path source_type)",
            },
            "url": {
                "type": "string",
                "required": False,
                "description": "URL to download CSV from (for url source_type)",
            },
            "delimiter": {
                "type": "select",
                "options": ["comma", "semicolon", "tab", "pipe"],
                "default": "comma",
                "required": False,
                "description": "Field delimiter used in the CSV file",
            },
            "encoding": {
                "type": "select",
                "options": SUPPORTED_ENCODINGS,
                "default": "utf-8",
                "required": False,
                "description": "Character encoding of the CSV file",
            },
            "has_header": {
                "type": "boolean",
                "default": True,
                "required": False,
                "description": "Whether the first row contains column headers",
            },
            "skip_rows": {
                "type": "integer",
                "default": 0,
                "required": False,
                "description": "Number of rows to skip at the beginning (before header)",
            },
            "table_name": {
                "type": "string",
                "default": "csv_data",
                "required": False,
                "description": "Name for the resulting table/stream",
            },
            "url_headers": {
                "type": "json",
                "required": False,
                "description": "Optional HTTP headers for URL fetch (JSON object)",
            },
            "quote_char": {
                "type": "string",
                "default": '"',
                "required": False,
                "description": "Character used to quote fields containing special characters",
            },
        }

    def _get_csv_content(self) -> str:
        """
        Retrieve CSV content based on source_type configuration.

        Returns:
            CSV content as a string

        Raises:
            CSVConnectorError: If content cannot be retrieved
        """
        if self._csv_content is not None:
            return self._csv_content

        source_type = self.config.get("source_type", "file_upload")
        encoding = self.config.get("encoding", "utf-8")

        if source_type == "file_upload":
            file_content = self.config.get("file_content")
            if not file_content:
                raise CSVConnectorError(
                    "file_content is required when source_type is 'file_upload'"
                )
            try:
                decoded = base64.b64decode(file_content)
                self._csv_content = decoded.decode(encoding)
            except base64.binascii.Error as e:
                raise CSVConnectorError(f"Invalid base64 content: {e}")
            except UnicodeDecodeError as e:
                raise CSVConnectorError(
                    f"Failed to decode content with encoding '{encoding}': {e}. "
                    f"Try a different encoding (e.g., 'latin-1', 'cp1252')."
                )

        elif source_type == "file_path":
            file_path = self.config.get("file_path")
            if not file_path:
                raise CSVConnectorError(
                    "file_path is required when source_type is 'file_path'"
                )

            # Security check: prevent path traversal
            file_path = os.path.abspath(file_path)

            if not os.path.exists(file_path):
                raise CSVConnectorError(f"File not found: {file_path}")

            if not os.path.isfile(file_path):
                raise CSVConnectorError(f"Path is not a file: {file_path}")

            try:
                with open(file_path, "r", encoding=encoding) as f:
                    self._csv_content = f.read()
            except UnicodeDecodeError as e:
                raise CSVConnectorError(
                    f"Failed to read file with encoding '{encoding}': {e}. "
                    f"Try a different encoding."
                )
            except PermissionError:
                raise CSVConnectorError(f"Permission denied reading file: {file_path}")
            except OSError as e:
                raise CSVConnectorError(f"Error reading file: {e}")

        elif source_type == "url":
            url = self.config.get("url")
            if not url:
                raise CSVConnectorError(
                    "url is required when source_type is 'url'"
                )

            # Validate URL
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https"):
                raise CSVConnectorError(
                    f"Invalid URL scheme: {parsed.scheme}. Only http and https are supported."
                )

            try:
                headers = self.config.get("url_headers", {}) or {}
                if isinstance(headers, str):
                    import json
                    headers = json.loads(headers)

                response = requests.get(
                    url,
                    headers=headers,
                    timeout=60,
                    stream=True,
                )
                response.raise_for_status()

                # Check content type
                content_type = response.headers.get("Content-Type", "").split(";")[0].strip()
                if content_type and content_type not in CSV_CONTENT_TYPES:
                    logger.warning(
                        f"URL returned unexpected content type: {content_type}. "
                        f"Proceeding anyway."
                    )

                # Read content with size limit (100MB)
                max_size = 100 * 1024 * 1024
                content_length = response.headers.get("Content-Length")
                if content_length and int(content_length) > max_size:
                    raise CSVConnectorError(
                        f"File too large: {int(content_length)} bytes. "
                        f"Maximum size is {max_size} bytes."
                    )

                # Download with size check
                chunks = []
                total_size = 0
                for chunk in response.iter_content(chunk_size=8192):
                    total_size += len(chunk)
                    if total_size > max_size:
                        raise CSVConnectorError(
                            f"File too large. Maximum size is {max_size} bytes."
                        )
                    chunks.append(chunk)

                content_bytes = b"".join(chunks)
                self._csv_content = content_bytes.decode(encoding)

            except requests.exceptions.Timeout:
                raise CSVConnectorError(f"Timeout downloading URL: {url}")
            except requests.exceptions.ConnectionError as e:
                raise CSVConnectorError(f"Connection error downloading URL: {e}")
            except requests.exceptions.HTTPError as e:
                raise CSVConnectorError(f"HTTP error downloading URL: {e}")
            except UnicodeDecodeError as e:
                raise CSVConnectorError(
                    f"Failed to decode URL content with encoding '{encoding}': {e}"
                )
        else:
            raise CSVConnectorError(f"Unknown source_type: {source_type}")

        return self._csv_content

    def _parse_csv(self) -> tuple[List[str], List[List[str]]]:
        """
        Parse CSV content into headers and rows.

        Returns:
            Tuple of (headers, rows)
        """
        if self._headers is not None and self._rows is not None:
            return self._headers, self._rows

        content = self._get_csv_content()
        delimiter_name = self.config.get("delimiter", "comma")
        delimiter = DELIMITER_MAP.get(delimiter_name, ",")
        has_header = self.config.get("has_header", True)
        skip_rows = self.config.get("skip_rows", 0) or 0
        quote_char = self.config.get("quote_char", '"') or '"'

        # Parse CSV
        reader = csv.reader(
            io.StringIO(content),
            delimiter=delimiter,
            quotechar=quote_char,
            skipinitialspace=True,
        )

        all_rows = list(reader)

        # Skip rows
        if skip_rows > 0:
            all_rows = all_rows[skip_rows:]

        if not all_rows:
            raise CSVConnectorError("CSV file is empty or all rows were skipped")

        # Extract headers
        if has_header:
            raw_headers = all_rows[0]
            self._headers = [_sanitize_column_name(h) for h in raw_headers]
            self._rows = all_rows[1:]
        else:
            # Auto-generate column names
            num_cols = max(len(row) for row in all_rows) if all_rows else 0
            self._headers = [f"column_{i+1}" for i in range(num_cols)]
            self._rows = all_rows

        # Ensure unique column names
        seen = {}
        unique_headers = []
        for h in self._headers:
            if h in seen:
                seen[h] += 1
                unique_headers.append(f"{h}_{seen[h]}")
            else:
                seen[h] = 0
                unique_headers.append(h)
        self._headers = unique_headers

        # Infer column types from data
        self._column_types = {}
        for i, header in enumerate(self._headers):
            sample_values = [
                row[i] for row in self._rows[:100]
                if i < len(row)
            ]
            self._column_types[header] = _infer_column_type(sample_values)

        logger.info(
            f"Parsed CSV: {len(self._headers)} columns, {len(self._rows)} rows"
        )

        return self._headers, self._rows

    def test_connection(self) -> bool:
        """
        Test that the CSV data can be read and parsed.

        Returns:
            True if successful

        Raises:
            CSVConnectorError: If CSV cannot be read or parsed
        """
        try:
            headers, rows = self._parse_csv()

            if not headers:
                raise CSVConnectorError("No columns found in CSV")

            logger.info(
                f"CSV connection test successful: {len(headers)} columns, "
                f"{len(rows)} rows"
            )
            return True

        except CSVConnectorError:
            raise
        except Exception as e:
            raise CSVConnectorError(f"Failed to parse CSV: {e}")

    def discover_schema(self) -> List[Dict[str, Any]]:
        """
        Discover the schema of the CSV file.

        Returns:
            List with a single table descriptor containing column information
        """
        headers, rows = self._parse_csv()

        columns = []
        for i, header in enumerate(headers):
            col_type = self._column_types.get(header, "string")
            columns.append({
                "name": header,
                "type": col_type,
                "nullable": True,
                "primary_key": i == 0,  # First column as default primary key
            })

        return [
            {
                "name": self._table_name,
                "description": f"Data from CSV file ({len(rows)} rows)",
                "columns": columns,
                "supports_incremental": False,
                "incremental_key": None,
            }
        ]

    def extract(
        self,
        tables: Optional[List[str]] = None,
        incremental_key: Optional[str] = None,
        last_value: Optional[Any] = None,
    ) -> Iterator[Dict[str, Any]]:
        """
        Extract data from the CSV file.

        Args:
            tables: List of table names to extract (ignored for CSV, always extracts all)
            incremental_key: Not supported for CSV files
            last_value: Not supported for CSV files

        Yields:
            Dict representing each row with type-converted values
        """
        headers, rows = self._parse_csv()

        logger.info(f"Extracting {len(rows)} rows from CSV")

        for row_idx, row in enumerate(rows):
            record = {}
            for col_idx, header in enumerate(headers):
                if col_idx < len(row):
                    raw_value = row[col_idx]
                    col_type = self._column_types.get(header, "string")
                    record[header] = _convert_value(raw_value, col_type)
                else:
                    record[header] = None

            # Add metadata
            record["_row_number"] = row_idx + 1
            record["_table"] = self._table_name
            record["_dlt_load_time"] = datetime.utcnow().isoformat()

            yield record

        logger.info(f"Extracted {len(rows)} records from CSV")

    def close(self):
        """Clean up any resources."""
        self._csv_content = None
        self._headers = None
        self._rows = None
        self._column_types = None
