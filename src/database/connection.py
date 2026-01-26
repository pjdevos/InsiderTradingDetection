"""
Database connection and session management
"""
import logging
import time
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import Pool

from config import config
from database.models import Base

logger = logging.getLogger(__name__)

# Global engine and session factory
_engine = None
_SessionFactory = None

# Retry settings for Railway private networking
MAX_RETRIES = 10
INITIAL_DELAY = 2  # seconds


def init_db(database_url: str = None, echo: bool = False):
    """
    Initialize database connection and create tables

    Args:
        database_url: Database connection string (defaults to config)
        echo: Whether to log SQL queries

    Note:
        Includes retry logic for Railway private networking DNS resolution
    """
    global _engine, _SessionFactory

    database_url = database_url or config.DATABASE_URL

    # Ensure SSL mode for Railway connections
    if database_url and 'railway' in database_url.lower() and 'sslmode' not in database_url:
        separator = '&' if '?' in database_url else '?'
        database_url = f"{database_url}{separator}sslmode=require"
        logger.info("Added sslmode=require for Railway connection")

    logger.info("Initializing database connection...")

    # Retry loop for Railway private networking DNS resolution
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            # Connection arguments for PostgreSQL reliability
            connect_args = {}
            if 'postgresql' in database_url:
                connect_args = {
                    'connect_timeout': 30,
                    'keepalives': 1,
                    'keepalives_idle': 30,
                    'keepalives_interval': 10,
                    'keepalives_count': 5,
                }

            # Create engine
            _engine = create_engine(
                database_url,
                echo=echo,
                pool_pre_ping=True,  # Verify connections before using
                pool_size=10,
                max_overflow=20,
                pool_recycle=3600,  # Recycle connections after 1 hour
                connect_args=connect_args,
            )

            # Add connection pool logging (only on first successful attempt)
            if attempt == 0:
                @event.listens_for(Pool, "connect")
                def receive_connect(dbapi_conn, connection_record):
                    logger.debug("Database connection established")

                @event.listens_for(Pool, "checkout")
                def receive_checkout(dbapi_conn, connection_record, connection_proxy):
                    logger.debug("Connection checked out from pool")

            # Create session factory
            _SessionFactory = sessionmaker(bind=_engine, expire_on_commit=False)

            # Create all tables - this is where connection actually happens
            Base.metadata.create_all(_engine)
            logger.info("Database tables created successfully")
            return _engine

        except Exception as e:
            last_error = e
            error_msg = str(e).lower()

            # Check if it's a DNS/network error (Railway private networking not ready)
            if "could not translate host name" in error_msg or \
               "name or service not known" in error_msg or \
               "connection refused" in error_msg or \
               "timeout" in error_msg or \
               "server closed the connection unexpectedly" in error_msg or \
               "connection reset" in error_msg or \
               "broken pipe" in error_msg:

                delay = INITIAL_DELAY * (2 ** attempt)  # Exponential backoff
                delay = min(delay, 30)  # Cap at 30 seconds

                logger.warning(
                    f"Database connection failed (attempt {attempt + 1}/{MAX_RETRIES}): {e}. "
                    f"Retrying in {delay}s..."
                )
                time.sleep(delay)
            else:
                # Non-retryable error
                logger.error(f"Error creating database connection: {e}", exc_info=True)
                raise

    # All retries exhausted
    logger.error(f"Failed to connect to database after {MAX_RETRIES} attempts")
    raise last_error


def get_engine():
    """Get the global database engine"""
    if _engine is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _engine


def get_session() -> Session:
    """
    Get a new database session

    Returns:
        SQLAlchemy Session object

    Note: Caller is responsible for closing the session
    """
    if _SessionFactory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    return _SessionFactory()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions

    Usage:
        with get_db_session() as session:
            # Use session
            session.add(obj)
            session.commit()

    Yields:
        SQLAlchemy Session object
    """
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database session error: {e}", exc_info=True)
        raise
    finally:
        session.close()


def close_db():
    """Close database connection and cleanup"""
    global _engine, _SessionFactory

    if _engine:
        _engine.dispose()
        logger.info("Database connection closed")

    _engine = None
    _SessionFactory = None


def drop_all_tables():
    """
    Drop all tables (use with caution!)

    Only use for testing or complete database reset
    """
    if _engine is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    logger.warning("Dropping all database tables...")
    Base.metadata.drop_all(_engine)
    logger.info("All tables dropped")


def create_all_tables():
    """
    Create all tables

    Safe to call multiple times - only creates missing tables
    """
    if _engine is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    logger.info("Creating database tables...")
    Base.metadata.create_all(_engine)
    logger.info("Tables created successfully")


# For testing - use SQLite in-memory database
def init_test_db():
    """Initialize in-memory SQLite database for testing"""
    return init_db('sqlite:///:memory:', echo=False)
