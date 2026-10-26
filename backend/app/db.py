"""Database connection pool shared by all API requests."""

import logging
from collections.abc import Iterator

from fastapi import Request
from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

logger = logging.getLogger(__name__)


def create_pool(database_url: str) -> ConnectionPool:
    # open=True with wait=False: the API starts even if the database is still booting;
    # requests then fail with 503 until a connection can be made.
    return ConnectionPool(
        conninfo=database_url,
        min_size=1,
        max_size=10,
        timeout=5,
        kwargs={"row_factory": dict_row, "autocommit": True},
        open=True,
        name="urbanvision",
    )


def get_connection(request: Request) -> Iterator[Connection]:
    """FastAPI dependency: borrow a connection from the pool for one request."""
    pool: ConnectionPool = request.app.state.pool
    with pool.connection() as conn:
        yield conn
