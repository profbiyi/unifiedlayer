"""
PostgreSQL Connector using dlt framework.

Provides complete PostgreSQL integration with CDC support via logical replication,
automatic schema detection, incremental loading, and connection pooling.

Supports parallel table extraction via dlt's parallelized resources,
allowing concurrent fetching of multiple tables for better performance.
"""
from typing import Iterator, Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
import psycopg2
from psycopg2 import pool, sql
from psycopg2.extras import RealDictCursor
import dlt
from dlt.sources import DltResource
from dlt.common.typing import TDataItem
import logging
import concurrent.futures
from functools import partial

logger = logging.getLogger(__name__)


class PostgreSQLError(Exception):
    """Custom exception for PostgreSQL connector errors."""
    pass


class PostgreSQLConnector:
    """
    Production-ready PostgreSQL connector with CDC support.

    Features:
    - Automatic schema detection
    - CDC support via logical replication (WAL)
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
        min_connections: int = 1,
        max_connections: int = 10,
        schema: str = "public",
        sslmode: Optional[str] = None,
        options: Optional[str] = None,
    ):
        """
        Initialize PostgreSQL connector.

        Args:
            host: Database host
            port: Database port
            database: Database name
            user: Database user
            password: Database password
            min_connections: Minimum connections in pool
            max_connections: Maximum connections in pool
            schema: Schema to use
            sslmode: SSL mode (e.g., 'require', 'prefer', 'disable')
            options: Additional connection options (e.g., for Neon endpoint)
        """
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.schema = schema

        # Create connection pool with SSL and options support
        try:
            conn_params = {
                "minconn": min_connections,
                "maxconn": max_connections,
                "host": host,
                "port": port,
                "database": database,
                "user": user,
                "password": password,
            }

            # Add SSL mode if specified
            if sslmode:
                conn_params["sslmode"] = sslmode

            # Add options if specified (e.g., for Neon endpoint)
            if options:
                conn_params["options"] = options

            self.connection_pool = psycopg2.pool.ThreadedConnectionPool(**conn_params)
            logger.info(f"Connection pool created for {database}@{host} (SSL: {sslmode or 'default'})")
        except psycopg2.Error as e:
            raise PostgreSQLError(f"Failed to create connection pool: {str(e)}")

    def get_connection(self):
        """Get connection from pool."""
        try:
            return self.connection_pool.getconn()
        except psycopg2.Error as e:
            raise PostgreSQLError(f"Failed to get connection from pool: {str(e)}")

    def return_connection(self, conn):
        """Return connection to pool."""
        self.connection_pool.putconn(conn)

    def get_tables(self) -> List[str]:
        """
        Get list of all tables in schema.

        Returns:
            List of table names
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            query = sql.SQL("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = %s
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)

            cursor.execute(query, (self.schema,))
            tables = [row[0] for row in cursor.fetchall()]

            cursor.close()
            logger.info(f"Found {len(tables)} tables in schema '{self.schema}'")
            return tables

        except psycopg2.Error as e:
            raise PostgreSQLError(f"Failed to get tables: {str(e)}")
        finally:
            if conn:
                self.return_connection(conn)

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
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            query = sql.SQL("""
                SELECT
                    column_name,
                    data_type,
                    is_nullable,
                    column_default,
                    character_maximum_length,
                    numeric_precision,
                    numeric_scale
                FROM information_schema.columns
                WHERE table_schema = %s
                AND table_name = %s
                ORDER BY ordinal_position
            """)

            cursor.execute(query, (self.schema, table_name))
            columns = cursor.fetchall()

            cursor.close()
            logger.info(f"Table '{table_name}' has {len(columns)} columns")
            return [dict(col) for col in columns]

        except psycopg2.Error as e:
            raise PostgreSQLError(f"Failed to get table schema: {str(e)}")
        finally:
            if conn:
                self.return_connection(conn)

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

            query = sql.SQL("""
                SELECT a.attname
                FROM pg_index i
                JOIN pg_attribute a ON a.attrelid = i.indrelid
                    AND a.attnum = ANY(i.indkey)
                WHERE i.indrelid = %s::regclass
                AND i.indisprimary
            """)

            full_table_name = f"{self.schema}.{table_name}"
            cursor.execute(query, (full_table_name,))
            pk_columns = [row[0] for row in cursor.fetchall()]

            cursor.close()
            return pk_columns if pk_columns else None

        except psycopg2.Error as e:
            logger.warning(f"Failed to get primary key for {table_name}: {str(e)}")
            return None
        finally:
            if conn:
                self.return_connection(conn)

    def fetch_table_data(
        self,
        table_name: str,
        cursor_column: Optional[str] = None,
        last_value: Optional[Any] = None,
        batch_size: int = 10000,
    ) -> Iterator[Dict[str, Any]]:
        """
        Fetch data from a table with optional incremental loading.

        Uses server-side cursor for efficient streaming of large datasets.

        Args:
            table_name: Name of the table
            cursor_column: Column for incremental loading (timestamp/id)
            last_value: Last value for incremental loading
            batch_size: Number of rows per batch

        Yields:
            Row data as dictionaries
        """
        conn = None
        rows_yielded = 0
        try:
            conn = self.get_connection()
            # Use server-side cursor for large datasets
            cursor = conn.cursor(name='fetch_cursor', cursor_factory=RealDictCursor)

            # Build query - no LIMIT for full table fetch
            if cursor_column and last_value:
                query = sql.SQL("""
                    SELECT * FROM {schema}.{table}
                    WHERE {cursor_col} > %s
                    ORDER BY {cursor_col}
                """).format(
                    schema=sql.Identifier(self.schema),
                    table=sql.Identifier(table_name),
                    cursor_col=sql.Identifier(cursor_column),
                )
                cursor.execute(query, (last_value,))
            else:
                # Full table fetch - no LIMIT, fetch all rows
                query = sql.SQL("""
                    SELECT * FROM {schema}.{table}
                """).format(
                    schema=sql.Identifier(self.schema),
                    table=sql.Identifier(table_name),
                )
                cursor.execute(query)

            logger.info(f"Executing query for table '{table_name}'")

            while True:
                rows = cursor.fetchmany(batch_size)
                if not rows:
                    break

                for row in rows:
                    row_dict = dict(row)
                    row_dict["_dlt_load_time"] = datetime.now().isoformat()
                    rows_yielded += 1
                    yield row_dict

            logger.info(f"Fetched {rows_yielded} rows from table '{table_name}'")
            cursor.close()

        except psycopg2.Error as e:
            logger.error(f"Failed to fetch data from {table_name}: {str(e)}")
            raise PostgreSQLError(f"Failed to fetch data from {table_name}: {str(e)}")
        finally:
            if conn:
                self.return_connection(conn)

    def setup_cdc_replication(self, slot_name: str = "dlt_replication_slot") -> bool:
        """
        Setup logical replication slot for CDC.

        Args:
            slot_name: Name of the replication slot

        Returns:
            True if successful
        """
        conn = None
        try:
            conn = self.get_connection()
            conn.autocommit = True
            cursor = conn.cursor()

            # Check if replication slot exists
            cursor.execute("""
                SELECT slot_name
                FROM pg_replication_slots
                WHERE slot_name = %s
            """, (slot_name,))

            if cursor.fetchone():
                logger.info(f"Replication slot '{slot_name}' already exists")
                cursor.close()
                return True

            # Create replication slot
            cursor.execute(
                sql.SQL("SELECT pg_create_logical_replication_slot(%s, 'pgoutput')"),
                (slot_name,)
            )

            logger.info(f"Created replication slot '{slot_name}'")
            cursor.close()
            return True

        except psycopg2.Error as e:
            logger.error(f"Failed to setup CDC replication: {str(e)}")
            return False
        finally:
            if conn:
                conn.autocommit = False
                self.return_connection(conn)

    def fetch_cdc_changes(
        self,
        slot_name: str = "dlt_replication_slot",
        batch_size: int = 1000,
    ) -> Iterator[Dict[str, Any]]:
        """
        Fetch changes from logical replication slot.

        Args:
            slot_name: Name of the replication slot
            batch_size: Number of changes per batch

        Yields:
            Change records
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            query = sql.SQL("""
                SELECT *
                FROM pg_logical_slot_get_changes(%s, NULL, %s)
            """)

            cursor.execute(query, (slot_name, batch_size))
            changes = cursor.fetchall()

            for change in changes:
                change_dict = dict(change)
                change_dict["_dlt_load_time"] = datetime.now().isoformat()
                yield change_dict

            cursor.close()

        except psycopg2.Error as e:
            raise PostgreSQLError(f"Failed to fetch CDC changes: {str(e)}")
        finally:
            if conn:
                self.return_connection(conn)

    def close(self):
        """Close all connections in pool."""
        if hasattr(self, 'connection_pool'):
            self.connection_pool.closeall()
            logger.info("Connection pool closed")


@dlt.source(name="postgres")
def postgres_source(
    host: str = dlt.secrets.value,
    port: int = 5432,
    database: str = dlt.secrets.value,
    user: str = dlt.secrets.value,
    password: str = dlt.secrets.value,
    schema: str = "public",
    tables: Optional[List[str]] = None,
    enable_cdc: bool = False,
    sslmode: Optional[str] = None,
    options: Optional[str] = None,
) -> List[DltResource]:
    """
    dlt source for PostgreSQL data.

    Provides automatic schema detection and incremental loading.

    Args:
        host: Database host
        port: Database port
        database: Database name
        user: Database user
        password: Database password
        schema: Schema to use
        tables: List of tables to load (None = all tables)
        enable_cdc: Enable CDC via logical replication
        sslmode: SSL mode (e.g., 'require', 'prefer', 'disable')
        options: Additional connection options (e.g., for Neon endpoint)

    Returns:
        List of dlt resources
    """
    connector = PostgreSQLConnector(
        host=host,
        port=port,
        database=database,
        user=user,
        password=password,
        schema=schema,
        sslmode=sslmode,
        options=options,
    )

    # Get tables to load
    all_tables = connector.get_tables()
    tables_to_load = tables if tables else all_tables

    resources = []

    for table in tables_to_load:
        if table not in all_tables:
            logger.warning(f"Table '{table}' not found in schema '{schema}'")
            continue

        # Get table schema and primary key
        table_schema = connector.get_table_schema(table)
        primary_key = connector.get_primary_key(table)

        # Find timestamp column for incremental loading
        timestamp_columns = [
            col["column_name"]
            for col in table_schema
            if col["data_type"] in ("timestamp", "timestamp with time zone", "timestamp without time zone")
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
            last_value: Optional[dlt.sources.incremental[Any]] = dlt.sources.incremental(
                cursor_column or "id",
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
        connector.setup_cdc_replication()

        @dlt.resource(name="cdc_changes", write_disposition="append", parallelized=True)
        def cdc_changes() -> Iterator[TDataItem]:
            """Load CDC changes from replication slot (parallelized)."""
            yield from connector.fetch_cdc_changes()

        resources.append(cdc_changes)

    logger.info(f"Created {len(resources)} parallelized resources for PostgreSQL extraction")
    return resources


if __name__ == "__main__":
    # Example usage
    pipeline = dlt.pipeline(
        pipeline_name="postgres_pipeline",
        destination="duckdb",
        dataset_name="postgres_data",
    )

    # Load data
    load_info = pipeline.run(
        postgres_source(
            host="localhost",
            database="mydb",
            user="user",
            password="password",
        )
    )
    logger.info(load_info)
