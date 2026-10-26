"""GTFS import orchestration.

The whole load runs in ONE database transaction: if anything fails, the previous
timetable stays untouched, and API users never see a half-imported feed.
"""

import logging
import tempfile
import time
from pathlib import Path

import psycopg

from ingestion.schema import apply_schema

from . import load
from .derive import build_derived_tables
from .source import download_feed, extract_feed, sha256_of
from .validate import GtfsFeed, GtfsValidationError, ImportReport, check_structure

logger = logging.getLogger(__name__)

GTFS_TABLES = [
    "route_stops",
    "service_dates",
    "stop_times",
    "trips",
    "shapes",
    "stops",
    "routes",
    "agencies",
    "calendar",
    "calendar_dates",
]


def import_gtfs(
    database_url: str,
    *,
    url: str | None = None,
    path: Path | None = None,
    download_dir: Path,
    user_agent: str,
    force: bool = False,
) -> ImportReport:
    """Import a GTFS feed from a URL, a local ZIP file or an already-extracted directory."""
    if (url is None) == (path is None):
        raise ValueError("Provide exactly one of `url` or `path`")

    started = time.perf_counter()
    report = ImportReport(source=url or str(path))

    if url is not None:
        path = download_feed(url, download_dir, user_agent)
    assert path is not None
    if not path.exists():
        raise GtfsValidationError(f"GTFS source not found: {path}")

    checksum = sha256_of(path) if path.is_file() else None
    with psycopg.connect(database_url) as conn:
        apply_schema(conn)
        conn.commit()
        if checksum and not force and _already_imported(conn, checksum):
            logger.info(
                "This exact feed (sha256 %s…) is already imported; use --force to redo",
                checksum[:12],
            )
            report.skipped = True
            return report

        with tempfile.TemporaryDirectory(dir=_temp_parent(download_dir)) as tmp:
            feed_dir = extract_feed(path, Path(tmp)) if path.is_file() else path
            feed = GtfsFeed(feed_dir)
            check_structure(feed)
            _load_everything(conn, feed, report, source=report.source, checksum=checksum)

        conn.commit()
        conn.autocommit = True
        conn.execute("ANALYZE")  # refresh planner statistics after a bulk load

    report.duration_seconds = round(time.perf_counter() - started, 1)
    logger.info("GTFS import finished in %.1fs: %s", report.duration_seconds, report.row_counts)
    for warning in report.warnings:
        logger.warning(warning)
    return report


def _temp_parent(download_dir: Path) -> Path:
    download_dir.mkdir(parents=True, exist_ok=True)
    return download_dir


def _already_imported(conn: psycopg.Connection, checksum: str) -> bool:
    row = conn.execute(
        "SELECT file_sha256 FROM feed_info ORDER BY imported_at DESC LIMIT 1"
    ).fetchone()
    return bool(row and row[0] == checksum)


def _load_everything(
    conn: psycopg.Connection,
    feed: GtfsFeed,
    report: ImportReport,
    *,
    source: str,
    checksum: str | None,
) -> None:
    with conn.cursor() as cur:
        cur.execute(f"TRUNCATE {', '.join(GTFS_TABLES)}")

        step = _Timer()
        agency_ids = load.load_agencies(cur, feed, report)
        route_ids = load.load_routes(cur, feed, report, agency_ids)
        stop_ids = load.load_stops(cur, feed, report)
        step.done("agencies, routes, stops")
        shape_ids = load.load_shapes(cur, feed, report)
        step.done("shapes")
        trip_ids = load.load_trips(cur, feed, report, route_ids, shape_ids)
        step.done("trips")
        load.load_stop_times(cur, feed, report, trip_ids, stop_ids)
        step.done("stop_times")
        load.load_calendar(cur, feed, report)
        load.load_calendar_dates(cur, feed, report)
        report.row_counts.update(build_derived_tables(cur))
        step.done("calendar + derived tables")

        if report.row_counts.get("service_dates", 0) == 0:
            raise GtfsValidationError("Feed defines no service dates; nothing would ever run")

        info = load.read_feed_info(feed)
        cur.execute(
            """
            INSERT INTO feed_info
                (publisher_name, feed_version, feed_start_date, feed_end_date, source, file_sha256)
            SELECT %(publisher_name)s, %(feed_version)s,
                   COALESCE(%(feed_start_date)s::date, min(service_date)),
                   COALESCE(%(feed_end_date)s::date, max(service_date)),
                   %(source)s, %(checksum)s
            FROM service_dates
            """,
            {**info, "source": source, "checksum": checksum},
        )


class _Timer:
    def __init__(self) -> None:
        self.last = time.perf_counter()

    def done(self, what: str) -> None:
        now = time.perf_counter()
        logger.info("Loaded %s in %.1fs", what, now - self.last)
        self.last = now
