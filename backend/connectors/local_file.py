"""
Local File System Connector.

Reads data from local filesystem paths. Supports CSV, JSON, JSONL (newline-delimited JSON),
and Parquet file formats with glob patterns for multiple files and directory scanning.

Useful for self-hosted deployments where users want to ingest files from mounted volumes.
"""
import csv
import glob
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Set

import dlt
from dlt.common.typing import TDataItem
from dlt.sources import DltResource

from backend.connectors.sdk.base import (
    AuthType,
    BaseConnector,
    ConnectorCapabilities,
    ConnectorMetadata,
    PaginationType,
)
from backend.connectors.sdk.registry import register_connector

logger = logging.getLogger(__name__)


class LocalFileError(Exception):
    """Custom exception for local file operations."""
    pass


# Supported file extensions
SUPPORTED_EXTENSIONS = {".csv", ".json", ".jsonl", ".parquet"}


def _infer_type_from_value(value: Any) -> str:
    """Infer a schema type from a Python value."""
    if value is None:
        return "string"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    return "string"


def _normalize_table_name(file_path: str) -> str:
    """Convert a file path to a valid table name."""
    name = Path(file_path).stem
    # Replace non-alphanumeric characters with underscores
    normalized = "".join(c if c.isalnum() else "_" for c in name)
    # Remove leading numbers and multiple underscores
    while normalized and normalized[0].isdigit():
        normalized = normalized[1:]
    normalized = "_".join(filter(None, normalized.split("_")))
    return normalized.lower() or "data"


def _get_file_extension(file_path: str) -> str:
    """Get the lowercase file extension."""
    return Path(file_path).suffix.lower()


def _expand_path(path: str) -> List[str]:
    """
    Expand a path into a list of matching files.

    Supports:
    - Single file paths
    - Glob patterns (e.g., /data/*.csv)
    - Directories (scans for supported files)
    """
    path = os.path.expanduser(path)
    path = os.path.expandvars(path)

    # Check if it's a glob pattern
    if any(c in path for c in "*?[]"):
        files = glob.glob(path, recursive=True)
        return sorted([f for f in files if os.path.isfile(f) and _get_file_extension(f) in SUPPORTED_EXTENSIONS])

    # Single file
    if os.path.isfile(path):
        ext = _get_file_extension(path)
        if ext in SUPPORTED_EXTENSIONS:
            return [path]
        raise LocalFileError(f"Unsupported file extension: {ext}. Supported: {SUPPORTED_EXTENSIONS}")

    # Directory - scan for supported files
    if os.path.isdir(path):
        files = []
        for ext in SUPPORTED_EXTENSIONS:
            files.extend(glob.glob(os.path.join(path, f"*{ext}")))
            files.extend(glob.glob(os.path.join(path, f"**/*{ext}"), recursive=True))
        return sorted(set(files))

    raise LocalFileError(f"Path does not exist: {path}")


def _read_csv_file(file_path: str, delimiter: str = ",", encoding: str = "utf-8") -> Iterator[Dict[str, Any]]:
    """Read records from a CSV file."""
    try:
        with open(file_path, "r", encoding=encoding, newline="") as f:
            # Detect delimiter if auto
            if delimiter == "auto":
                sample = f.read(8192)
                f.seek(0)
                sniffer = csv.Sniffer()
                try:
                    dialect = sniffer.sniff(sample, delimiters=",;\t|")
                    delimiter = dialect.delimiter
                except csv.Error:
                    delimiter = ","

            reader = csv.DictReader(f, delimiter=delimiter)
            for row in reader:
                yield dict(row)
    except UnicodeDecodeError as e:
        raise LocalFileError(f"Encoding error reading {file_path}: {e}. Try specifying encoding.")
    except Exception as e:
        raise LocalFileError(f"Error reading CSV file {file_path}: {e}")


def _read_json_file(file_path: str, encoding: str = "utf-8") -> Iterator[Dict[str, Any]]:
    """Read records from a JSON file. Expects an array of objects or a single object."""
    try:
        with open(file_path, "r", encoding=encoding) as f:
            data = json.load(f)

        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    yield item
                else:
                    yield {"value": item}
        elif isinstance(data, dict):
            yield data
        else:
            yield {"value": data}
    except json.JSONDecodeError as e:
        raise LocalFileError(f"Invalid JSON in {file_path}: {e}")
    except Exception as e:
        raise LocalFileError(f"Error reading JSON file {file_path}: {e}")


def _read_jsonl_file(file_path: str, encoding: str = "utf-8") -> Iterator[Dict[str, Any]]:
    """Read records from a JSONL (newline-delimited JSON) file."""
    try:
        with open(file_path, "r", encoding=encoding) as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    if isinstance(record, dict):
                        yield record
                    else:
                        yield {"value": record}
                except json.JSONDecodeError as e:
                    logger.warning(f"Skipping invalid JSON on line {line_num} in {file_path}: {e}")
    except Exception as e:
        raise LocalFileError(f"Error reading JSONL file {file_path}: {e}")


def _read_parquet_file(file_path: str) -> Iterator[Dict[str, Any]]:
    """Read records from a Parquet file."""
    try:
        import pyarrow.parquet as pq
    except ImportError:
        raise LocalFileError(
            "pyarrow is required to read Parquet files. Install with: pip install pyarrow"
        )

    try:
        table = pq.read_table(file_path)
        for batch in table.to_batches():
            for row in batch.to_pylist():
                yield row
    except Exception as e:
        raise LocalFileError(f"Error reading Parquet file {file_path}: {e}")


def _read_file(
    file_path: str,
    delimiter: str = ",",
    encoding: str = "utf-8",
) -> Iterator[Dict[str, Any]]:
    """Read records from a file based on its extension."""
    ext = _get_file_extension(file_path)

    if ext == ".csv":
        yield from _read_csv_file(file_path, delimiter, encoding)
    elif ext == ".json":
        yield from _read_json_file(file_path, encoding)
    elif ext == ".jsonl":
        yield from _read_jsonl_file(file_path, encoding)
    elif ext == ".parquet":
        yield from _read_parquet_file(file_path)
    else:
        raise LocalFileError(f"Unsupported file extension: {ext}")


def _sample_file(file_path: str, sample_size: int = 100, **kwargs) -> List[Dict[str, Any]]:
    """Read a sample of records from a file for schema inference."""
    samples = []
    for i, record in enumerate(_read_file(file_path, **kwargs)):
        samples.append(record)
        if i >= sample_size - 1:
            break
    return samples


def _infer_schema_from_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Infer column schema from a list of records."""
    if not records:
        return []

    # Collect all keys and sample values
    columns_info: Dict[str, Set[str]] = {}

    for record in records:
        for key, value in record.items():
            if key not in columns_info:
                columns_info[key] = set()
            if value is not None:
                columns_info[key].add(_infer_type_from_value(value))

    # Build column list
    columns = []
    for col_name, types in columns_info.items():
        # Resolve type conflicts (prefer more specific types)
        if not types:
            col_type = "string"
        elif len(types) == 1:
            col_type = next(iter(types))
        elif "number" in types and "integer" in types:
            col_type = "number"
        else:
            col_type = "string"  # Fallback to string for mixed types

        columns.append({
            "name": col_name,
            "type": col_type,
            "primary_key": col_name.lower() in ("id", "_id"),
        })

    return columns


class LocalFileReader:
    """
    Local file reader with support for multiple formats.

    Features:
    - CSV, JSON, JSONL, Parquet support
    - Glob patterns for multiple files
    - Directory scanning
    - File filtering by extension
    """

    def __init__(
        self,
        path: str,
        file_extensions: Optional[List[str]] = None,
        csv_delimiter: str = ",",
        encoding: str = "utf-8",
        recursive: bool = True,
    ):
        self.path = path
        self.file_extensions = set(file_extensions) if file_extensions else SUPPORTED_EXTENSIONS
        self.csv_delimiter = csv_delimiter
        self.encoding = encoding
        self.recursive = recursive

        # Validate extensions
        for ext in self.file_extensions:
            if ext not in SUPPORTED_EXTENSIONS:
                raise LocalFileError(f"Unsupported extension: {ext}. Supported: {SUPPORTED_EXTENSIONS}")

    def list_files(self) -> List[str]:
        """List all matching files."""
        all_files = _expand_path(self.path)

        # Filter by extension if specified
        if self.file_extensions != SUPPORTED_EXTENSIONS:
            all_files = [
                f for f in all_files
                if _get_file_extension(f) in self.file_extensions
            ]

        return all_files

    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Get metadata about a file."""
        stat = os.stat(file_path)
        return {
            "path": file_path,
            "name": os.path.basename(file_path),
            "extension": _get_file_extension(file_path),
            "size_bytes": stat.st_size,
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
        }

    def read_file(self, file_path: str) -> Iterator[Dict[str, Any]]:
        """Read all records from a specific file."""
        yield from _read_file(
            file_path,
            delimiter=self.csv_delimiter,
            encoding=self.encoding,
        )

    def read_all(self) -> Iterator[Dict[str, Any]]:
        """Read all records from all matching files."""
        files = self.list_files()

        for file_path in files:
            logger.info(f"Reading file: {file_path}")
            table_name = _normalize_table_name(file_path)

            try:
                for record in self.read_file(file_path):
                    # Add metadata
                    record["_source_file"] = file_path
                    record["_source_table"] = table_name
                    record["_dlt_load_time"] = datetime.now().isoformat()
                    yield record
            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")
                raise

    def infer_schema(self, file_path: str, sample_size: int = 100) -> Dict[str, Any]:
        """Infer schema for a single file."""
        samples = _sample_file(
            file_path,
            sample_size=sample_size,
            delimiter=self.csv_delimiter,
            encoding=self.encoding,
        )

        columns = _infer_schema_from_records(samples)
        file_info = self.get_file_info(file_path)

        return {
            "name": _normalize_table_name(file_path),
            "description": f"Data from {file_info['name']} ({file_info['extension']})",
            "columns": columns,
            "supports_incremental": True,
            "incremental_key": "_dlt_load_time",
            "file_path": file_path,
            "file_size_bytes": file_info["size_bytes"],
            "sample_record_count": len(samples),
        }


@register_connector
class LocalFileConnector(BaseConnector):
    """
    Local file system connector.

    Reads data from local filesystem paths with support for:
    - CSV, JSON, JSONL, Parquet file formats
    - Glob patterns for multiple files (e.g., /data/*.csv)
    - Directory scanning
    - File filtering by extension

    Useful for self-hosted deployments with mounted volumes.
    """

    metadata = ConnectorMetadata(
        name="local_file",
        display_name="Local File System",
        description="Read data from local files. Supports CSV, JSON, JSONL, and Parquet formats with glob patterns.",
        icon="folder",
        category="file",
        version="1.0.0",
        capabilities=ConnectorCapabilities(
            supports_incremental=True,
            supports_schema_discovery=True,
            supports_connection_test=True,
            supports_parallel_extraction=True,
            max_concurrent_tables=4,
            auth_types=[AuthType.NONE],
            pagination_type=PaginationType.NONE,
        ),
        supported_tables=[],  # Dynamic based on discovered files
    )

    def setup(self):
        """Initialize the connector with configuration."""
        self._path = self.config.require("path")
        self._file_extensions = self.config.get("file_extensions")
        self._csv_delimiter = self.config.get("csv_delimiter", ",")
        self._encoding = self.config.get("encoding", "utf-8")
        self._recursive = self.config.get("recursive", True)

        # Parse file extensions if provided as string
        if isinstance(self._file_extensions, str):
            self._file_extensions = [ext.strip() for ext in self._file_extensions.split(",")]

        # Ensure extensions have leading dot
        if self._file_extensions:
            self._file_extensions = [
                ext if ext.startswith(".") else f".{ext}"
                for ext in self._file_extensions
            ]

        self._reader: Optional[LocalFileReader] = None

    def _get_reader(self) -> LocalFileReader:
        """Get or create the file reader."""
        if self._reader is None:
            self._reader = LocalFileReader(
                path=self._path,
                file_extensions=self._file_extensions,
                csv_delimiter=self._csv_delimiter,
                encoding=self._encoding,
                recursive=self._recursive,
            )
        return self._reader

    def get_config_schema(self) -> Dict[str, Any]:
        """Return the configuration schema."""
        return {
            "type": "object",
            "required": ["path"],
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path, directory path, or glob pattern (e.g., /data/*.csv, /mnt/data/)",
                },
                "file_extensions": {
                    "type": "array",
                    "description": "File extensions to include (e.g., ['.csv', '.json']). Defaults to all supported formats.",
                    "items": {"type": "string"},
                    "default": [".csv", ".json", ".jsonl", ".parquet"],
                },
                "csv_delimiter": {
                    "type": "string",
                    "description": "Delimiter for CSV files. Use 'auto' for auto-detection.",
                    "default": ",",
                },
                "encoding": {
                    "type": "string",
                    "description": "File encoding (e.g., utf-8, latin-1).",
                    "default": "utf-8",
                },
                "recursive": {
                    "type": "boolean",
                    "description": "Recursively scan directories for files.",
                    "default": True,
                },
            },
        }

    def test_connection(self) -> Dict[str, Any]:
        """Test that the configured path is accessible."""
        try:
            reader = self._get_reader()
            files = reader.list_files()

            if not files:
                return {
                    "success": False,
                    "message": f"No supported files found at path: {self._path}",
                }

            # Group files by extension
            by_extension: Dict[str, int] = {}
            total_size = 0

            for f in files:
                ext = _get_file_extension(f)
                by_extension[ext] = by_extension.get(ext, 0) + 1
                total_size += os.path.getsize(f)

            extension_summary = ", ".join(f"{count} {ext}" for ext, count in sorted(by_extension.items()))
            size_mb = total_size / (1024 * 1024)

            return {
                "success": True,
                "message": f"Found {len(files)} file(s): {extension_summary}. Total size: {size_mb:.2f} MB",
                "details": {
                    "file_count": len(files),
                    "files_by_extension": by_extension,
                    "total_size_bytes": total_size,
                    "sample_files": files[:5],
                },
            }
        except LocalFileError as e:
            return {"success": False, "message": str(e)}
        except PermissionError as e:
            return {"success": False, "message": f"Permission denied: {e}"}
        except Exception as e:
            return {"success": False, "message": f"Unexpected error: {e}"}

    def discover_schema(self) -> List[Dict[str, Any]]:
        """Discover schemas from available files."""
        reader = self._get_reader()
        files = reader.list_files()

        schemas = []
        for file_path in files:
            try:
                schema = reader.infer_schema(file_path)
                schemas.append(schema)
            except Exception as e:
                logger.warning(f"Could not infer schema for {file_path}: {e}")

        return schemas

    def extract(
        self,
        tables: Optional[List[str]] = None,
        table_name: Optional[str] = None,
        file_path: Optional[str] = None,
        incremental_key: Optional[str] = None,
        last_value: Optional[Any] = None,
        **kwargs,
    ) -> Iterator[Dict[str, Any]]:
        """
        Extract data from files.

        Args:
            tables: List of table names (file stems) to extract.
            table_name: Single table name to extract (alternative to tables).
            file_path: Specific file path to extract from.
            incremental_key: Column for incremental extraction.
            last_value: Last value seen for incremental key.

        Yields:
            Records from the specified files.
        """
        reader = self._get_reader()

        # If specific file path provided, use it directly
        if file_path:
            if not os.path.isfile(file_path):
                raise LocalFileError(f"File not found: {file_path}")

            logger.info(f"Extracting from specific file: {file_path}")
            table = _normalize_table_name(file_path)

            for record in reader.read_file(file_path):
                record["_source_file"] = file_path
                record["_source_table"] = table
                record["_dlt_load_time"] = datetime.now().isoformat()

                # Apply incremental filter if specified
                if incremental_key and last_value:
                    if record.get(incremental_key) is not None:
                        if record[incremental_key] <= last_value:
                            continue

                yield record
            return

        # Get list of files to process
        all_files = reader.list_files()

        # Filter by table names if specified
        target_tables = set()
        if tables:
            target_tables = set(tables)
        elif table_name:
            target_tables = {table_name}

        files_to_process = []
        for f in all_files:
            normalized = _normalize_table_name(f)
            if not target_tables or normalized in target_tables:
                files_to_process.append((f, normalized))

        if target_tables and not files_to_process:
            available = [_normalize_table_name(f) for f in all_files]
            raise LocalFileError(
                f"No files found matching tables: {target_tables}. "
                f"Available: {available}"
            )

        logger.info(f"Extracting {len(files_to_process)} file(s)")

        for file_path, table in files_to_process:
            logger.info(f"Extracting: {file_path} -> {table}")

            for record in reader.read_file(file_path):
                record["_source_file"] = file_path
                record["_source_table"] = table
                record["_dlt_load_time"] = datetime.now().isoformat()

                # Apply incremental filter if specified
                if incremental_key and last_value:
                    if record.get(incremental_key) is not None:
                        if record[incremental_key] <= last_value:
                            continue

                yield record

    def close(self):
        """Cleanup resources."""
        self._reader = None


@dlt.source(name="local_files")
def local_files_source(
    path: str = dlt.config.value,
    file_extensions: Optional[List[str]] = None,
    csv_delimiter: str = ",",
    encoding: str = "utf-8",
    recursive: bool = True,
) -> List[DltResource]:
    """
    dlt source for local file data.

    Creates a resource for each discovered file.

    Args:
        path: File path, directory, or glob pattern.
        file_extensions: List of extensions to include.
        csv_delimiter: Delimiter for CSV files.
        encoding: File encoding.
        recursive: Scan directories recursively.

    Returns:
        List of dlt resources, one per file.
    """
    reader = LocalFileReader(
        path=path,
        file_extensions=file_extensions,
        csv_delimiter=csv_delimiter,
        encoding=encoding,
        recursive=recursive,
    )

    files = reader.list_files()
    logger.info(f"Discovered {len(files)} files at path: {path}")

    resources = []

    for file_path in files:
        table_name = _normalize_table_name(file_path)

        @dlt.resource(
            name=table_name,
            write_disposition="merge",
            primary_key="_source_file",
            parallelized=True,
        )
        def file_data(
            fp=file_path,
            tn=table_name,
            rdr=reader,
        ) -> Iterator[TDataItem]:
            logger.info(f"Reading file: {fp}")
            for record in rdr.read_file(fp):
                record["_source_file"] = fp
                record["_source_table"] = tn
                record["_dlt_load_time"] = datetime.now().isoformat()
                yield record

        resources.append(file_data)

    logger.info(f"Created {len(resources)} resources for local file extraction")
    return resources
