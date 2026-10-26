"""Shared test fixtures.

Database tests run against a separate database (POSTGRES_TEST_DB, default
`urbanvision_test`) in the same PostgreSQL server; it is created automatically.
They are skipped with a clear message when PostgreSQL is not running.
"""

from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg.rows import dict_row

from app.config import Settings, get_settings
from app.main import create_app
from ingestion.gtfs.importer import import_gtfs

FIXTURES = Path(__file__).parent / "fixtures"
MINI_GTFS = FIXTURES / "mini_gtfs"


@pytest.fixture(scope="session")
def settings() -> Settings:
    base = get_settings()
    return base.model_copy(update={"postgres_db": base.postgres_test_db, "bkk_api_key": None})


@pytest.fixture(scope="session")
def database_url(settings: Settings) -> str:
    try:
        with psycopg.connect(
            settings.database_url("postgres"), autocommit=True, connect_timeout=3
        ) as conn:
            exists = conn.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s", (settings.postgres_db,)
            ).fetchone()
            if not exists:
                conn.execute(f'CREATE DATABASE "{settings.postgres_db}"')
    except psycopg.OperationalError as exc:
        pytest.skip(f"PostgreSQL is not reachable (run `docker compose up -d db`): {exc}")
    return settings.database_url()


def import_mini_feed(database_url: str, tmp_path: Path, feed_dir: Path = MINI_GTFS):
    return import_gtfs(
        database_url, path=feed_dir, download_dir=tmp_path, user_agent="tests", force=True
    )


@pytest.fixture(scope="session")
def import_report(database_url: str, tmp_path_factory):
    return import_mini_feed(database_url, tmp_path_factory.mktemp("gtfs"))


@pytest.fixture
def db(database_url: str, import_report):
    with psycopg.connect(database_url, row_factory=dict_row, autocommit=True) as conn:
        yield conn


@pytest.fixture(scope="session")
def client(settings: Settings, import_report):
    with TestClient(create_app(settings)) as test_client:
        yield test_client
