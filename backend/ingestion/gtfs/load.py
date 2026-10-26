"""Clean each GTFS file with pandas and bulk-load it into PostgreSQL with COPY.

Every loader returns the set of IDs it stored, so later files can drop rows that
reference something missing (e.g. a trip whose route does not exist).
"""

import io
import logging

import pandas as pd
import psycopg

from app.config import BUDAPEST_BOUNDS
from app.transport_modes import mode_for_route_type

from .validate import (
    GtfsFeed,
    ImportReport,
    blank_to_na,
    parse_color,
    parse_float,
    parse_gtfs_date,
    parse_gtfs_time,
    parse_int,
)

logger = logging.getLogger(__name__)

STOP_TIMES_CHUNK_ROWS = 500_000
DEFAULT_AGENCY_ID = "DEFAULT"
KEPT_LOCATION_TYPES = {0, 1}  # stops/platforms and stations; entrances & nodes are not needed


def copy_frame(cur: psycopg.Cursor, table: str, frame: pd.DataFrame, columns: list[str]) -> int:
    """Bulk insert a DataFrame via COPY (much faster than INSERT). Empty values become NULL."""
    if frame.empty:
        return 0
    buffer = io.StringIO()
    frame[columns].to_csv(buffer, index=False, header=False)
    with cur.copy(f"COPY {table} ({', '.join(columns)}) FROM STDIN WITH (FORMAT csv)") as copy:
        copy.write(buffer.getvalue())
    return len(frame)


def _drop(frame: pd.DataFrame, mask: pd.Series, report: ImportReport, reason: str) -> pd.DataFrame:
    dropped = int(mask.sum())
    if dropped:
        report.warn(f"{reason}: {dropped} row(s) dropped")
    return frame[~mask]


def _dedupe(frame: pd.DataFrame, keys: list[str], report: ImportReport, file: str) -> pd.DataFrame:
    return _drop(frame, frame.duplicated(keys, keep="first"), report, f"{file}: duplicate {keys}")


def load_agencies(cur: psycopg.Cursor, feed: GtfsFeed, report: ImportReport) -> set[str]:
    df = feed.read("agency.txt")
    df["agency_id"] = df["agency_id"].replace("", DEFAULT_AGENCY_ID)
    df = _dedupe(df, ["agency_id"], report, "agency.txt")
    out = pd.DataFrame(
        {
            "agency_id": df["agency_id"],
            "name": df["agency_name"],
            "url": blank_to_na(df["agency_url"]),
            "timezone": blank_to_na(df["agency_timezone"]),
            "phone": blank_to_na(df["agency_phone"]),
        }
    )
    report.row_counts["agencies"] = copy_frame(cur, "agencies", out, list(out.columns))
    return set(out["agency_id"])


def load_routes(
    cur: psycopg.Cursor, feed: GtfsFeed, report: ImportReport, agency_ids: set[str]
) -> set[str]:
    df = _dedupe(feed.read("routes.txt"), ["route_id"], report, "routes.txt")
    route_type = parse_int(df["route_type"])
    df = _drop(df, route_type.isna(), report, "routes.txt: invalid route_type")
    route_type = route_type[df.index]

    agency = df["agency_id"]
    if len(agency_ids) == 1:  # agency_id may be omitted in single-agency feeds
        agency = agency.replace("", next(iter(agency_ids)))
    unknown_agency = ~agency.isin(agency_ids)
    if unknown_agency.any():
        report.warn(f"routes.txt: {int(unknown_agency.sum())} route(s) with unknown agency_id")

    out = pd.DataFrame(
        {
            "route_id": df["route_id"],
            "agency_id": agency.where(~unknown_agency, None),
            "short_name": blank_to_na(df["route_short_name"]),
            "long_name": blank_to_na(df["route_long_name"]),
            "description": blank_to_na(df["route_desc"]),
            "route_type": route_type,
            "mode": route_type.map(lambda value: mode_for_route_type(int(value))),
            "color": parse_color(df["route_color"]),
            "text_color": parse_color(df["route_text_color"]),
            "sort_order": parse_int(df["route_sort_order"]),
        }
    )
    report.row_counts["routes"] = copy_frame(cur, "routes", out, list(out.columns))
    return set(out["route_id"])


def load_stops(cur: psycopg.Cursor, feed: GtfsFeed, report: ImportReport) -> set[str]:
    df = _dedupe(feed.read("stops.txt"), ["stop_id"], report, "stops.txt")
    location_type = parse_int(df["location_type"]).fillna(0)
    ignored = ~location_type.isin(list(KEPT_LOCATION_TYPES))
    if ignored.any():
        logger.info("Skipping %d entrances/nodes/boarding areas", int(ignored.sum()))
    df, location_type = df[~ignored], location_type[~ignored]

    lat, lon = parse_float(df["stop_lat"]), parse_float(df["stop_lon"])
    bad_coords = (
        lat.isna()
        | lon.isna()
        | ~lat.between(-90, 90)
        | ~lon.between(-180, 180)
        | ((lat == 0) & (lon == 0))
    ).fillna(True)
    df = _drop(df, bad_coords, report, "stops.txt: missing or invalid coordinates")
    lat, lon, location_type = lat[df.index], lon[df.index], location_type[df.index]

    outside = ~(
        lat.between(BUDAPEST_BOUNDS["min_lat"], BUDAPEST_BOUNDS["max_lat"])
        & lon.between(BUDAPEST_BOUNDS["min_lon"], BUDAPEST_BOUNDS["max_lon"])
    )
    if outside.any():  # informational only: HÉV lines legitimately leave the city
        logger.info("%d stop(s) lie outside the Budapest bounding box", int(outside.sum()))

    names = df["stop_name"].where(df["stop_name"] != "", "Stop " + df["stop_id"])
    kept_ids = set(df["stop_id"])
    stations = set(df.loc[location_type == 1, "stop_id"])
    parent = df["parent_station"].where(df["parent_station"].isin(stations), None)
    orphan_parents = int(((df["parent_station"] != "") & parent.isna()).sum())
    if orphan_parents:
        report.warn(f"stops.txt: {orphan_parents} parent_station reference(s) cleared")

    out = pd.DataFrame(
        {
            "stop_id": df["stop_id"],
            "stop_code": blank_to_na(df["stop_code"]),
            "name": names,
            "geom": "SRID=4326;POINT(" + lon.astype(str) + " " + lat.astype(str) + ")",
            "location_type": location_type,
            "parent_station": parent,
            "wheelchair_boarding": parse_int(df["wheelchair_boarding"]),
        }
    )
    report.row_counts["stops"] = copy_frame(cur, "stops", out, list(out.columns))
    return kept_ids


def load_shapes(cur: psycopg.Cursor, feed: GtfsFeed, report: ImportReport) -> set[str]:
    """Collapse shape points into one LineString per shape_id."""
    if not feed.has("shapes.txt"):
        report.row_counts["shapes"] = 0
        return set()
    df = feed.read("shapes.txt")
    points = pd.DataFrame(
        {
            "shape_id": df["shape_id"],
            "seq": parse_int(df["shape_pt_sequence"]),
            "lon": parse_float(df["shape_pt_lon"]),
            "lat": parse_float(df["shape_pt_lat"]),
        }
    )
    points = _drop(points, points.isna().any(axis=1), report, "shapes.txt: invalid point")
    cur.execute(
        "CREATE TEMP TABLE shape_points (shape_id TEXT, seq INT, lon FLOAT8, lat FLOAT8)"
        " ON COMMIT DROP"
    )
    copy_frame(cur, "shape_points", points, ["shape_id", "seq", "lon", "lat"])
    cur.execute(
        """
        INSERT INTO shapes (shape_id, geom)
        SELECT shape_id, ST_MakeLine(ST_SetSRID(ST_MakePoint(lon, lat), 4326) ORDER BY seq)
        FROM shape_points
        GROUP BY shape_id
        HAVING count(*) >= 2
        """
    )
    report.row_counts["shapes"] = cur.rowcount
    cur.execute("SELECT shape_id FROM shapes")
    return {row[0] for row in cur.fetchall()}


def load_trips(
    cur: psycopg.Cursor,
    feed: GtfsFeed,
    report: ImportReport,
    route_ids: set[str],
    shape_ids: set[str],
) -> set[str]:
    df = _dedupe(feed.read("trips.txt"), ["trip_id"], report, "trips.txt")
    df = _drop(df, ~df["route_id"].isin(route_ids), report, "trips.txt: unknown route_id")
    direction = parse_int(df["direction_id"])
    out = pd.DataFrame(
        {
            "trip_id": df["trip_id"],
            "route_id": df["route_id"],
            "service_id": df["service_id"],
            "headsign": blank_to_na(df["trip_headsign"]),
            "direction_id": direction.where(direction.isin([0, 1])),
            "shape_id": df["shape_id"].where(df["shape_id"].isin(shape_ids), None),
            "wheelchair_accessible": parse_int(df["wheelchair_accessible"]),
            "bikes_allowed": parse_int(df["bikes_allowed"]),
        }
    )
    report.row_counts["trips"] = copy_frame(cur, "trips", out, list(out.columns))
    return set(out["trip_id"])


def load_stop_times(
    cur: psycopg.Cursor,
    feed: GtfsFeed,
    report: ImportReport,
    trip_ids: set[str],
    stop_ids: set[str],
    chunksize: int = STOP_TIMES_CHUNK_ROWS,
) -> None:
    """The biggest file (~440 MB for Budapest) is streamed in chunks to limit memory use."""
    total = orphans = bad_rows = 0
    columns = [
        "trip_id",
        "stop_sequence",
        "stop_id",
        "arrival_secs",
        "departure_secs",
        "stop_headsign",
        "pickup_type",
        "drop_off_type",
    ]
    for chunk in feed.read_chunks("stop_times.txt", chunksize):
        orphan = ~chunk["trip_id"].isin(trip_ids) | ~chunk["stop_id"].isin(stop_ids)
        orphans += int(orphan.sum())
        chunk = chunk[~orphan]

        sequence = parse_int(chunk["stop_sequence"])
        arrival = parse_gtfs_time(chunk["arrival_time"])
        departure = parse_gtfs_time(chunk["departure_time"])
        # A timepoint may give only one of the two times; use it for both.
        arrival, departure = arrival.fillna(departure), departure.fillna(arrival)
        invalid = sequence.isna() | (
            ((chunk["arrival_time"] != "") & arrival.isna())
            | ((chunk["departure_time"] != "") & departure.isna())
        )
        bad_rows += int(invalid.sum())
        keep = ~invalid

        out = pd.DataFrame(
            {
                "trip_id": chunk["trip_id"],
                "stop_sequence": sequence,
                "stop_id": chunk["stop_id"],
                "arrival_secs": arrival,
                "departure_secs": departure,
                "stop_headsign": blank_to_na(chunk["stop_headsign"]),
                "pickup_type": parse_int(chunk["pickup_type"]),
                "drop_off_type": parse_int(chunk["drop_off_type"]),
            }
        )[keep]
        out = out[~out.duplicated(["trip_id", "stop_sequence"])]
        total += copy_frame(cur, "stop_times", out, columns)
        logger.info("  stop_times: %s rows loaded", f"{total:,}")

    if orphans:
        report.warn(f"stop_times.txt: unknown trip_id/stop_id: {orphans} row(s) dropped")
    if bad_rows:
        report.warn(f"stop_times.txt: invalid time or sequence: {bad_rows} row(s) dropped")
    report.row_counts["stop_times"] = total


def load_calendar(cur: psycopg.Cursor, feed: GtfsFeed, report: ImportReport) -> None:
    if not feed.has("calendar.txt"):
        report.row_counts["calendar"] = 0
        return
    df = _dedupe(feed.read("calendar.txt"), ["service_id"], report, "calendar.txt")
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    out = pd.DataFrame({"service_id": df["service_id"]})
    for day in days:
        out[day] = df[day] == "1"
    out["start_date"] = parse_gtfs_date(df["start_date"])
    out["end_date"] = parse_gtfs_date(df["end_date"])
    out = _drop(
        out,
        out[["start_date", "end_date"]].isna().any(axis=1),
        report,
        "calendar.txt: invalid date",
    )
    report.row_counts["calendar"] = copy_frame(cur, "calendar", out, list(out.columns))


def load_calendar_dates(cur: psycopg.Cursor, feed: GtfsFeed, report: ImportReport) -> None:
    if not feed.has("calendar_dates.txt"):
        report.row_counts["calendar_dates"] = 0
        return
    df = feed.read("calendar_dates.txt")
    out = pd.DataFrame(
        {
            "service_id": df["service_id"],
            "date": parse_gtfs_date(df["date"]),
            "exception_type": parse_int(df["exception_type"]),
        }
    )
    invalid = out["date"].isna() | ~out["exception_type"].isin([1, 2]).fillna(False)
    out = _drop(out, invalid, report, "calendar_dates.txt: invalid date or exception_type")
    out = out[~out.duplicated(["service_id", "date"], keep="last")]
    report.row_counts["calendar_dates"] = copy_frame(cur, "calendar_dates", out, list(out.columns))


def read_feed_info(feed: GtfsFeed) -> dict[str, str | None]:
    info: dict[str, str | None] = {
        "publisher_name": None,
        "feed_version": None,
        "feed_start_date": None,
        "feed_end_date": None,
    }
    if not feed.has("feed_info.txt"):
        return info
    df = feed.read("feed_info.txt")
    if df.empty:
        return info
    row = df.iloc[0]
    info["publisher_name"] = row["feed_publisher_name"] or None
    info["feed_version"] = row["feed_version"] or None
    for key in ("feed_start_date", "feed_end_date"):
        parsed = parse_gtfs_date(pd.Series([row[key]])).iloc[0]
        info[key] = None if pd.isna(parsed) else str(parsed)
    return info
