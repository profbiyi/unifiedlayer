"""
Database configuration and session management.

Provides SQLAlchemy engine, session management, and FastAPI dependencies.
"""
from typing import Generator
from sqlalchemy import create_engine, event, pool, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import Engine
import logging

from backend.config import settings

logger = logging.getLogger(__name__)

# Create database engine with connection pooling
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=pool.QueuePool,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,  # Verify connections before using
    pool_recycle=3600,  # Recycle connections after 1 hour
    echo=settings.DATABASE_ECHO,  # Log SQL statements
)

# Create sessionmaker
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Base class for ORM models
Base = declarative_base()


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """
    Set connection parameters on connect.

    For PostgreSQL, we can set various parameters here.
    """
    # Check if this is a PostgreSQL connection by trying to detect the driver
    try:
        if hasattr(dbapi_conn, '__class__') and 'psycopg' in str(dbapi_conn.__class__):
            cursor = dbapi_conn.cursor()
            cursor.execute("SET timezone='UTC'")
            cursor.close()
    except Exception:
        # If it fails, it's not PostgreSQL or the command isn't supported
        pass


@event.listens_for(Engine, "checkout")
def receive_checkout(dbapi_conn, connection_record, connection_proxy):
    """Log when a connection is checked out from the pool."""
    logger.debug("Connection checked out from pool")


@event.listens_for(Engine, "checkin")
def receive_checkin(dbapi_conn, connection_record):
    """Log when a connection is returned to the pool."""
    logger.debug("Connection returned to pool")


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database sessions.

    Yields a SQLAlchemy session and ensures it's closed after use.

    Usage:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Initialize database by creating all tables.

    This should be called on application startup.
    """
    logger.info("Initializing database...")

    # Import all models to ensure they're registered

    # Create all tables (checkfirst=True prevents errors with multiple workers)
    Base.metadata.create_all(bind=engine, checkfirst=True)

    logger.info("Database initialized successfully")


def drop_db() -> None:
    """
    Drop all database tables.

    WARNING: This will delete all data!
    Only use in development/testing.
    """
    if settings.ENVIRONMENT == "production":
        raise RuntimeError("Cannot drop database in production environment")

    logger.warning("Dropping all database tables...")
    Base.metadata.drop_all(bind=engine)
    logger.warning("All tables dropped")


def get_db_session() -> Session:
    """
    Get a database session for use outside FastAPI.

    Remember to close the session when done:
        db = get_db_session()
        try:
            # Use db
            pass
        finally:
            db.close()
    """
    return SessionLocal()


class DatabaseHealthCheck:
    """Database health check utility."""

    @staticmethod
    def check() -> bool:
        """
        Check database connectivity.

        Returns:
            True if database is accessible
        """
        try:
            db = SessionLocal()
            # SQLAlchemy 2.0 requires text() — a bare string raises
            # ObjectNotExecutableError, which made this check falsely report
            # the DB as down even while the app served queries fine.
            db.execute(text("SELECT 1"))
            db.close()
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return False

    @staticmethod
    def get_stats() -> dict:
        """
        Get database connection pool statistics.

        Returns:
            Dictionary with pool statistics
        """
        return {
            "pool_size": engine.pool.size(),
            "checked_in": engine.pool.checkedin(),
            "checked_out": engine.pool.checkedout(),
            "overflow": engine.pool.overflow(),
            "total_connections": engine.pool.size() + engine.pool.overflow(),
        }
