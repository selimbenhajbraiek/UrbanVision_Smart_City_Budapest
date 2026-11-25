"""Command-line entry point for data ingestion.

Examples:
    python -m ingestion init-db
    python -m ingestion gtfs                      # download the official BKK feed
    python -m ingestion gtfs --file feed.zip      # import a local ZIP (or extracted folder)
    python -m ingestion osm                       # import all OpenStreetMap layers
    python -m ingestion osm --layer ev_charging
    python -m ingestion create-admin --email admin@example.com   # asks for a password
"""

import argparse
import getpass
import logging
import sys
from pathlib import Path

import psycopg

from app.config import get_settings
from app.logging_config import setup_logging
from app.urban_layers import URBAN_LAYERS
from ingestion.gtfs.importer import import_gtfs
from ingestion.gtfs.source import GtfsSourceError
from ingestion.gtfs.validate import GtfsValidationError
from ingestion.osm import OverpassError, import_urban_layers
from ingestion.schema import apply_schema

logger = logging.getLogger("ingestion")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m ingestion",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--test-db", action="store_true", help="target the test database (POSTGRES_TEST_DB) instead"
    )
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("init-db", help="create tables and indexes")

    gtfs = commands.add_parser("gtfs", help="import a GTFS timetable feed")
    source = gtfs.add_mutually_exclusive_group()
    source.add_argument("--url", help="download from this URL (default: GTFS_URL setting)")
    source.add_argument("--file", type=Path, help="local GTFS .zip file or extracted directory")
    gtfs.add_argument("--force", action="store_true", help="re-import even if unchanged")

    osm = commands.add_parser("osm", help="import OpenStreetMap urban layers via Overpass")
    osm.add_argument(
        "--layer",
        action="append",
        choices=sorted(URBAN_LAYERS),
        help="layer to import (repeatable; default: all)",
    )

    admin = commands.add_parser(
        "create-admin", help="create an admin account (or promote / reset an existing one)"
    )
    admin.add_argument("--email", required=True)
    admin.add_argument(
        "--password", help="omit to be asked securely (recommended: it then stays out of history)"
    )

    args = parser.parse_args(argv)
    settings = get_settings()
    setup_logging(settings.log_level)
    database_url = settings.database_url(settings.postgres_test_db if args.test_db else None)

    try:
        if args.command == "init-db":
            with psycopg.connect(database_url, autocommit=True) as conn:
                apply_schema(conn)
        elif args.command == "gtfs":
            report = import_gtfs(
                database_url,
                url=None if args.file else (args.url or settings.gtfs_url),
                path=args.file,
                download_dir=settings.gtfs_download_dir,
                user_agent=settings.user_agent,
                force=args.force,
            )
            if not report.skipped:
                print(f"\nImported GTFS in {report.duration_seconds}s")
                for table, count in report.row_counts.items():
                    print(f"  {table:<22}{count:>10,}")
                print(f"  warnings: {len(report.warnings)}")
        elif args.command == "osm":
            counts = import_urban_layers(
                database_url,
                args.layer or list(URBAN_LAYERS),
                settings.overpass_url,
                settings.user_agent,
            )
            for layer_id, count in counts.items():
                print(f"  {layer_id:<16}{count:>6} features")
        elif args.command == "create-admin":
            return create_admin(database_url, args.email, args.password)
    except (GtfsSourceError, GtfsValidationError, OverpassError) as exc:
        logger.error("%s", exc)
        return 1
    except psycopg.OperationalError as exc:
        logger.error(
            "Cannot connect to the database. Is `docker compose up -d db` running?\n%s", exc
        )
        return 1
    return 0


def create_admin(database_url: str, email: str, password: str | None) -> int:
    from psycopg.rows import dict_row

    from app.repositories import users as users_repo
    from app.security import hash_password

    email = email.strip().lower()
    if password is None:
        password = getpass.getpass("Password (min. 8 characters): ")
        if password != getpass.getpass("Repeat password: "):
            logger.error("Passwords do not match")
            return 1
    if len(password) < 8:
        logger.error("Password must be at least 8 characters")
        return 1
    with psycopg.connect(database_url, autocommit=True, row_factory=dict_row) as conn:
        apply_schema(conn)
        existing = users_repo.get_by_email_with_hash(conn, email)
        if existing:
            users_repo.update(conn, existing["id"], role="admin", is_active=True)
            users_repo.set_password(conn, existing["id"], hash_password(password))
            print(f"Existing user {email} is now an admin (password updated).")
        else:
            users_repo.create(conn, email, hash_password(password), role="admin")
            print(f"Admin account {email} created.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
