import logging

import psycopg

from app.config import BACKEND_DIR

logger = logging.getLogger(__name__)

SCHEMA_FILE = BACKEND_DIR / "db" / "schema.sql"


def apply_schema(conn: psycopg.Connection) -> None:
    """Create extensions, tables and indexes if they do not exist yet."""
    conn.execute(SCHEMA_FILE.read_text(encoding="utf-8"))
    logger.info("Database schema is up to date")
