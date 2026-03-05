"""
HTTP File Connector.

Allows ingestion of CSV, JSONL, or Parquet files from public HTTP/HTTPS URLs.
Uses dlt's filesystem source which natively supports HTTP endpoints.

Supported URL formats:
    https://example.com/data.csv
    https://cdn.example.com/exports/transactions.jsonl
    https://storage.example.com/data.parquet

Configuration schema:
    url: str            — full HTTPS URL to the file or directory
    file_format: str    — "csv", "jsonl", "parquet" (auto-detected if omitted)
    table_name: str     — destination table name (default: derived from filename)
    delimiter: str      — CSV delimiter (default: ",")
    has_header: bool    — CSV has header row (default: True)
    encoding: str       — file encoding (default: "utf-8")
"""
import logging
import re
import urllib.error
import urllib.request
from typing import Any, Dict

logger = logging.getLogger(__name__)


class HttpFileConnector:
    """
    Connector for syncing files from public HTTP/HTTPS URLs.

    Wraps dlt's filesystem source to handle:
    - Auto format detection from URL extension
    - CSV, JSONL, Parquet formats
    - Single file or directory of files at a URL prefix
    """

    # Map of file extension -> dlt reader function name
    FORMAT_READERS = {
        "csv": "read_csv",
        "jsonl": "read_jsonl",
        "ndjson": "read_jsonl",
        "parquet": "read_parquet",
    }

    def __init__(self, config: Dict[str, Any]):
        self.url = config["url"]
        self.file_format = config.get("file_format") or self._detect_format(self.url)
        self.table_name = config.get("table_name") or self._derive_table_name(self.url)
        self.delimiter = config.get("delimiter", ",")
        self.has_header = config.get("has_header", True)
        self.encoding = config.get("encoding", "utf-8")

    def _detect_format(self, url: str) -> str:
        """Auto-detect format from URL file extension."""
        lower = url.lower().split("?")[0]  # strip query params
        for ext in ["parquet", "jsonl", "ndjson", "csv"]:
            if lower.endswith(f".{ext}"):
                return ext
        return "csv"  # default to CSV

    def _derive_table_name(self, url: str) -> str:
        """Derive a clean table name from the URL filename."""
        filename = url.split("/")[-1].split("?")[0]  # strip query params
        name = filename.rsplit(".", 1)[0]  # remove extension
        name = re.sub(r"[^a-z0-9_]", "_", name.lower())
        name = re.sub(r"_+", "_", name).strip("_")
        return name or "http_data"

    def get_dlt_source(self):
        """
        Build and return the dlt source for this HTTP file.

        Returns a dlt source that can be passed to pipeline.run().
        """
        from dlt.sources.filesystem import filesystem, read_csv, read_jsonl, read_parquet

        if self.file_format not in self.FORMAT_READERS:
            raise ValueError(
                f"Unsupported file format '{self.file_format}'. "
                f"Supported: {list(self.FORMAT_READERS.keys())}"
            )

        logger.info(
            "HttpFileConnector: loading %s format from %s -> table '%s'",
            self.file_format, self.url, self.table_name,
        )

        # For CSV, pass reader options; for others use defaults
        if self.file_format == "csv":
            reader = read_csv(
                sep=self.delimiter,
                encoding=self.encoding,
            )
        elif self.file_format in ("jsonl", "ndjson"):
            reader = read_jsonl()
        else:
            reader = read_parquet()

        # dlt filesystem source supports HTTP URLs natively
        source = filesystem(bucket_url=self.url) | reader
        return source

    def test_connection(self) -> Dict[str, Any]:
        """Test that the URL is reachable and returns expected content."""
        try:
            req = urllib.request.Request(self.url, method="HEAD")
            with urllib.request.urlopen(req, timeout=10) as resp:
                content_type = resp.headers.get("Content-Type", "")
                content_length = resp.headers.get("Content-Length", "unknown")
                return {
                    "success": True,
                    "url": self.url,
                    "format": self.file_format,
                    "content_type": content_type,
                    "content_length": content_length,
                    "table_name": self.table_name,
                }
        except urllib.error.HTTPError as e:
            return {
                "success": False,
                "error": f"HTTP {e.code}: {e.reason}",
                "url": self.url,
            }
        except urllib.error.URLError as e:
            return {
                "success": False,
                "error": f"URL error: {e.reason}",
                "url": self.url,
            }
        except Exception as e:
            return {"success": False, "error": str(e), "url": self.url}

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Return the configuration schema for the source wizard UI."""
        return {
            "type": "object",
            "required": ["url"],
            "properties": {
                "url": {
                    "type": "string",
                    "title": "File URL",
                    "description": "Public HTTPS URL to a CSV, JSONL, or Parquet file",
                    "placeholder": "https://example.com/data.csv",
                },
                "file_format": {
                    "type": "string",
                    "title": "File Format",
                    "description": "Auto-detected from URL extension if not set",
                    "enum": ["csv", "jsonl", "parquet"],
                    "default": None,
                },
                "table_name": {
                    "type": "string",
                    "title": "Destination Table Name",
                    "description": (
                        "Table name in your data warehouse "
                        "(auto-derived from filename if not set)"
                    ),
                    "placeholder": "sales_data",
                },
                "delimiter": {
                    "type": "string",
                    "title": "CSV Delimiter",
                    "description": "Only for CSV files",
                    "default": ",",
                },
                "has_header": {
                    "type": "boolean",
                    "title": "CSV Has Header Row",
                    "default": True,
                },
                "encoding": {
                    "type": "string",
                    "title": "File Encoding",
                    "description": "Only for CSV/JSONL files",
                    "default": "utf-8",
                },
            },
        }


def create_http_file_source(config: Dict[str, Any]):
    """
    Factory function called by pipeline_flow.py for source_type='http_file'.

    Returns a tuple of (dlt_source, table_name).
    The table_name is used by pipeline_flow to name the destination table.
    """
    connector = HttpFileConnector(config)
    return connector.get_dlt_source(), connector.table_name
