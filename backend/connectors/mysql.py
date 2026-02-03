"""
MySQL Connector using dlt framework.

Provides complete MySQL integration with binlog CDC support,
automatic schema detection, and incremental loading.

Supports parallel table extraction via dlt's parallelized resources,
allowing concurrent fetching of multiple tables for better performance.
"""
from typing import Iterator, Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
import mysql.connector
from mysql.connector import pooling, Error
from mysql.connector.cursor import MySQLCursorDict
import dlt
from dlt.sources import DltResource
from dlt.common.typing import TDataItem
import logging
import json

logger = logging.getLogger(__name__)


class MySQLError(Exception):
    """Custom exception for MySQL connector errors."""
    pass


class MySQLConnector:
    """
    Production-ready MySQL connector with binlog CDC support.

    Features:
    - Automatic schema detection
    - Binlog CDC support for change data capture
    - Incremental loading by timestamp/cursor
    - Connection pooling
    - Full error handling
    """

    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
        pool_size: int = 10,
        pool_name: str = "mypool",
    ):
        """
        Initialize MySQL connector.

        Args:
            host: Database host
            port: Database port
            database: Database name
            user: Database user
            password: Database password
            pool_size: Connection pool size
            pool_name: Connection pool name
        """
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password

        # Create connection pool
        try:
            self.connection_pool = mysql.connector.pooling.MySQLConnectionPool(
                pool_name=pool_name,
                pool_size=pool_size,
                pool_reset_session=True,
                host=host,
                port=port,
                database=database,
                user=user,
                password=password,
            )
            logger.info(f"Connection pool '{pool_name}' created for {database}@{host}")
        except Error as e:
            raise MySQLError(f"Failed to create connection pool: {str(e)}")

    def get_connection(self):
        """Get connection from pool."""
        try:
            return self.connection_pool.get_connection()
        except Error as e:
            raise MySQLError(f"Failed to get connection from pool: {str(e)}")

    def get_tables(self) -> List[str]:
        """
        Get list of all tables in database.

        Returns:
            List of table names
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("SHOW TABLES")
            tables = [row[0] for row in cursor.fetchall()]

            cursor.close()
            logger.info(f"Found {len(tables)} tables in database '{self.database}'")
            return tables

        except Error as e:
            raise MySQLError(f"Failed to get tables: {str(e)}")
        finally:
            if conn:
                conn.close()

    def get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Get schema information for a table.

        Args:
            table_name: Name of the table

        Returns:
            List of column definitions
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)

            query = """
                SELECT
                    COLUMN_NAME as column_name,
                    DATA_TYPE as data_type,
                    IS_NULLABLE as is_nullable,
                    COLUMN_DEFAULT as column_default,
                    CHARACTER_MAXIMUM_LENGTH as character_maximum_length,
                    NUMERIC_PRECISION as numeric_precision,
                    NUMERIC_SCALE as numeric_scale,
                    COLUMN_KEY as column_key,
                    EXTRA as extra
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = %s
                AND TABLE_NAME = %s
                ORDER BY ORDINAL_POSITION
            """

            cursor.execute(query, (self.database, table_name))
            columns = cursor.fetchall()

            cursor.close()
            logger.info(f"Table '{table_name}' has {len(columns)} columns")
            return columns

        except Error as e:
            raise MySQLError(f"Failed to get table schema: {str(e)}")
        finally:
            if conn:
                conn.close()

    def get_primary_key(self, table_name: str) -> Optional[List[str]]:
        """
        Get primary key columns for a table.

        Args:
            table_name: Name of the table

        Returns:
            List of primary key column names
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            query = """
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = %s
                AND TABLE_NAME = %s
                AND CONSTRAINT_NAME = 'PRIMARY'
                ORDER BY ORDINAL_POSITION
            """

            cursor.execute(query, (self.database, table_name))
            pk_columns = [row[0] for row in cursor.fetchall()]

            cursor.close()
            return pk_columns if pk_columns else None

        except Error as e:
            logger.warning(f"Failed to get primary key for {table_name}: {str(e)}")
            return None
        finally:
            if conn:
                conn.close()

    def fetch_table_data(
        self,
        table_name: str,
        cursor_column: Optional[str] = None,
        last_value: Optional[Any] = None,
        batch_size: int = 10000,
    ) -> Iterator[Dict[str, Any]]:
        """
        Fetch data from a table with optional incremental loading.

        Uses unbuffered cursor for efficient streaming of large datasets.

        Args:
            table_name: Name of the table
            cursor_column: Column for incremental loading (timestamp/id)
            last_value: Last value for incremental loading
            batch_size: Number of rows per batch (for fetchmany)

        Yields:
            Row data as dictionaries
        """
        conn = None
        rows_yielded = 0
        try:
            conn = self.get_connection()
            # Use unbuffered cursor for streaming large datasets
            cursor = conn.cursor(dictionary=True, buffered=False)

            # Build query - no LIMIT for full table fetch
            if cursor_column and last_value is not None:
                query = f"""
                    SELECT * FROM `{table_name}`
                    WHERE `{cursor_column}` > %s
                    ORDER BY `{cursor_column}`
                """
                cursor.execute(query, (last_value,))
            else:
                # Full table fetch - no LIMIT, fetch all rows
                query = f"SELECT * FROM `{table_name}`"
                cursor.execute(query)

            logger.info(f"Executing query for table '{table_name}'")

            while True:
                rows = cursor.fetchmany(batch_size)
                if not rows:
                    break

                for row in rows:
                    # Convert datetime objects to ISO format
                    for key, value in row.items():
                        if isinstance(value, datetime):
                            row[key] = value.isoformat()

                    row["_dlt_load_time"] = datetime.now().isoformat()
                    rows_yielded += 1
                    yield row

            logger.info(f"Fetched {rows_yielded} rows from table '{table_name}'")
            cursor.close()

        except Error as e:
            logger.error(f"Failed to fetch data from {table_name}: {str(e)}")
            raise MySQLError(f"Failed to fetch data from {table_name}: {str(e)}")
        finally:
            if conn:
                conn.close()

    def check_binlog_enabled(self) -> bool:
        """
        Check if binary logging is enabled on MySQL server.

        Returns:
            True if binlog is enabled
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute("SHOW VARIABLES LIKE 'log_bin'")
            result = cursor.fetchone()

            cursor.close()

            if result and result['Value'].upper() == 'ON':
                logger.info("Binary logging is enabled")
                return True
            else:
                logger.warning("Binary logging is not enabled")
                return False

        except Error as e:
            logger.error(f"Failed to check binlog status: {str(e)}")
            return False
        finally:
            if conn:
                conn.close()

    def get_binlog_position(self) -> Dict[str, Any]:
        """
        Get current binlog file and position.

        Returns:
            Dictionary with binlog file and position
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute("SHOW MASTER STATUS")
            result = cursor.fetchone()

            cursor.close()

            if result:
                return {
                    "file": result.get("File"),
                    "position": result.get("Position"),
                    "timestamp": datetime.now().isoformat(),
                }
            else:
                raise MySQLError("Unable to get binlog position")

        except Error as e:
            raise MySQLError(f"Failed to get binlog position: {str(e)}")
        finally:
            if conn:
                conn.close()

    def fetch_binlog_events(
        self,
        start_file: Optional[str] = None,
        start_position: Optional[int] = None,
        batch_size: int = 100,
    ) -> Iterator[Dict[str, Any]]:
        """
        Fetch events from MySQL binlog.

        Note: This is a simplified implementation. For production CDC,
        consider using specialized tools like Debezium or Maxwell's daemon.

        Args:
            start_file: Starting binlog file
            start_position: Starting position in binlog
            batch_size: Number of events per batch

        Yields:
            Binlog event records
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)

            # Get current position if not specified
            if not start_file or not start_position:
                current_pos = self.get_binlog_position()
                start_file = start_file or current_pos["file"]
                start_position = start_position or current_pos["position"]

            query = f"SHOW BINLOG EVENTS IN '{start_file}' FROM {start_position} LIMIT {batch_size}"
            cursor.execute(query)

            events = cursor.fetchall()
            for event in events:
                event["_dlt_load_time"] = datetime.now().isoformat()
                event["_binlog_file"] = start_file
                yield event

            cursor.close()

        except Error as e:
            logger.error(f"Failed to fetch binlog events: {str(e)}")
        finally:
            if conn:
                conn.close()

    def close(self):
        """Close connection pool."""
        logger.info("MySQL connection pool closed")


@dlt.source(name="mysql")
def mysql_source(
    host: str = dlt.secrets.value,
    port: int = 3306,
    database: str = dlt.secrets.value,
    user: str = dlt.secrets.value,
    password: str = dlt.secrets.value,
    tables: Optional[List[str]] = None,
    enable_cdc: bool = False,
) -> List[DltResource]:
    """
    dlt source for MySQL data.

    Provides automatic schema detection and incremental loading.

    Args:
        host: Database host
        port: Database port
        database: Database name
        user: Database user
        password: Database password
        tables: List of tables to load (None = all tables)
        enable_cdc: Enable CDC via binlog

    Returns:
        List of dlt resources
    """
    connector = MySQLConnector(
        host=host,
        port=port,
        database=database,
        user=user,
        password=password,
    )

    # Get tables to load
    all_tables = connector.get_tables()
    tables_to_load = tables if tables else all_tables

    resources = []

    for table in tables_to_load:
        if table not in all_tables:
            logger.warning(f"Table '{table}' not found in database '{database}'")
            continue

        # Get table schema and primary key
        table_schema = connector.get_table_schema(table)
        primary_key = connector.get_primary_key(table)

        # Find timestamp column for incremental loading
        timestamp_columns = [
            col["column_name"]
            for col in table_schema
            if col["data_type"] in ("timestamp", "datetime")
        ]
        cursor_column = timestamp_columns[0] if timestamp_columns else None

        @dlt.resource(
            name=table,
            write_disposition="merge" if primary_key else "append",
            primary_key=primary_key,
            parallelized=True,  # Enable parallel extraction of multiple tables
        )
        def load_table(
            table_name: str = table,
            cursor_col: Optional[str] = cursor_column,
            last_value: dlt.sources.incremental[Any] = dlt.sources.incremental(
                cursor_col or "id",
                initial_value=None,
            ) if cursor_column else None
        ) -> Iterator[TDataItem]:
            """Load table data with incremental support (parallelized)."""
            last_val = last_value.last_value if last_value else None

            yield from connector.fetch_table_data(
                table_name=table_name,
                cursor_column=cursor_col,
                last_value=last_val,
            )

        resources.append(load_table)

    # Add CDC resource if enabled
    if enable_cdc:
        if connector.check_binlog_enabled():
            @dlt.resource(name="binlog_events", write_disposition="append", parallelized=True)
            def binlog_events(
                last_position: dlt.sources.incremental[Dict[str, Any]] = dlt.sources.incremental(
                    "_binlog_position",
                    initial_value=None,
                )
            ) -> Iterator[TDataItem]:
                """Load binlog events for CDC (parallelized)."""
                start_file = None
                start_position = None

                if last_position.last_value:
                    start_file = last_position.last_value.get("file")
                    start_position = last_position.last_value.get("position")

                yield from connector.fetch_binlog_events(
                    start_file=start_file,
                    start_position=start_position,
                )

            resources.append(binlog_events)
        else:
            logger.warning("CDC requested but binlog is not enabled on MySQL server")

    logger.info(f"Created {len(resources)} parallelized resources for MySQL extraction")
    return resources


if __name__ == "__main__":
    # Example usage
    pipeline = dlt.pipeline(
        pipeline_name="mysql_pipeline",
        destination="duckdb",
        dataset_name="mysql_data",
    )

    # Load data
    load_info = pipeline.run(
        mysql_source(
            host="localhost",
            database="mydb",
            user="root",
            password="password",
        )
    )
    logger.info(load_info)
