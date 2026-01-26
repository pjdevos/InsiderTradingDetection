from logging.config import fileConfig
import sys
import time
import logging
from pathlib import Path

from sqlalchemy import engine_from_config, create_engine
from sqlalchemy import pool

from alembic import context

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

# Import our models and config
from database.models import Base
from config import config as app_config

logger = logging.getLogger('alembic.env')

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Get database URL and ensure SSL mode for Railway
database_url = app_config.DATABASE_URL
if database_url and 'railway' in database_url.lower() and 'sslmode' not in database_url:
    # Railway requires SSL
    separator = '&' if '?' in database_url else '?'
    database_url = f"{database_url}{separator}sslmode=require"

# Set the database URL from our app config
config.set_main_option('sqlalchemy.url', database_url)

# Retry settings for Railway
MAX_RETRIES = 5
RETRY_DELAY = 3  # seconds

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    Includes retry logic for Railway networking issues.
    """
    # Get connection config
    configuration = config.get_section(config.config_ini_section, {})

    # Add connection arguments for better reliability
    connect_args = {}

    # For PostgreSQL, add connection timeout
    if 'postgresql' in database_url:
        connect_args = {
            'connect_timeout': 30,
            'keepalives': 1,
            'keepalives_idle': 30,
            'keepalives_interval': 10,
            'keepalives_count': 5,
        }

    last_error = None

    for attempt in range(MAX_RETRIES):
        try:
            # Create engine with retry-friendly settings
            connectable = create_engine(
                database_url,
                poolclass=pool.NullPool,
                connect_args=connect_args,
            )

            with connectable.connect() as connection:
                context.configure(
                    connection=connection, target_metadata=target_metadata
                )

                with context.begin_transaction():
                    context.run_migrations()

            # Success - exit retry loop
            return

        except Exception as e:
            last_error = e
            error_msg = str(e).lower()

            # Check if it's a retryable error
            retryable = any(pattern in error_msg for pattern in [
                'connection refused',
                'could not translate host name',
                'name or service not known',
                'timeout',
                'server closed the connection unexpectedly',
                'connection reset',
                'broken pipe',
            ])

            if retryable and attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (2 ** attempt)  # Exponential backoff
                wait_time = min(wait_time, 30)  # Cap at 30 seconds
                logger.warning(
                    f"Database connection failed (attempt {attempt + 1}/{MAX_RETRIES}): {e}. "
                    f"Retrying in {wait_time}s..."
                )
                time.sleep(wait_time)
            else:
                # Non-retryable error or out of retries
                raise

    # All retries exhausted
    if last_error:
        raise last_error


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
