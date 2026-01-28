"""Web process entry point for Railway.

Runs alembic migrations (best-effort) then starts Streamlit.
Migrations failing must NOT prevent Streamlit from starting,
otherwise Railway's health check kills the container.
"""
import subprocess
import sys
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migrations():
    """Run alembic upgrade head. Returns True on success."""
    try:
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            timeout=30,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            logger.info("Migrations completed successfully")
        else:
            logger.warning(f"Migration failed (rc={result.returncode}): {result.stderr}")
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        logger.warning("Migration timed out after 30s, starting web anyway")
        return False
    except Exception as e:
        logger.warning(f"Migration error: {e}")
        return False


def start_streamlit():
    """Start Streamlit, replacing this process."""
    port = os.environ.get("PORT", "8501")
    os.execvp("streamlit", [
        "streamlit", "run", "dashboard.py",
        "--server.address", "0.0.0.0",
        "--server.port", port,
        "--server.headless", "true",
    ])


if __name__ == "__main__":
    run_migrations()
    start_streamlit()
