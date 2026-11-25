"""SQL for the route planner: the walking network and a slice of the timetable."""

from psycopg import Connection
from psycopg.rows import tuple_row

from app.repositories.departures import ServiceWindow

# Bounding-box pre-filter in degrees (uses the spatial index), refined with the exact
# distance. 0.004° ≈ 445 m north-south and ≈ 300 m east-west at Budapest's latitude.
_NEAR_DEG = 0.004


def boarding_stops(conn: Connection) -> list[tuple]:
    """(stop_id, name, lat, lon) of every stop served by at least one line."""
    with conn.cursor(row_factory=tuple_row) as cur:
        return cur.execute(
            """
            SELECT stop_id, name, ST_Y(geom), ST_X(geom)
            FROM stops
            WHERE location_type = 0 AND cardinality(modes) > 0
            """
        ).fetchall()


def footpaths(conn: Connection, max_meters: float) -> list[tuple]:
    """(from_stop, to_stop, meters) for boarding stops within walking distance of each other."""
    with conn.cursor(row_factory=tuple_row) as cur:
        return cur.execute(
            """
            SELECT a.stop_id, b.stop_id, ST_Distance(a.geom::geography, b.geom::geography)
            FROM stops a
            JOIN stops b
              ON b.stop_id <> a.stop_id AND ST_DWithin(a.geom, b.geom, %(near)s)
            WHERE a.location_type = 0 AND cardinality(a.modes) > 0
              AND b.location_type = 0 AND cardinality(b.modes) > 0
              AND ST_Distance(a.geom::geography, b.geom::geography) <= %(max)s
            """,
            {"near": _NEAR_DEG, "max": max_meters},
        ).fetchall()


def latest_schedule_second(conn: Connection) -> int:
    """Latest departure time in the feed (GTFS seconds; > 86400 for after-midnight trips)."""
    row = conn.execute("SELECT max(departure_secs) AS s FROM stop_times").fetchone()
    return row["s"] or 0


def timetable_slice(conn: Connection, windows: list[ServiceWindow]) -> list[tuple]:
    """Every scheduled stop event inside the windows, for trips running on that service day.

    Rows: (service_date, trip_id, stop_sequence, stop_id, rel_arrival, rel_departure,
    pickup_type, drop_off_type). `rel_*` are seconds after the request moment, so events
    of different service days (e.g. yesterday's 24:30 trip) share one timeline.
    """
    values = ", ".join(["(%s::date, %s::int, %s::int)"] * len(windows))
    params = [v for w in windows for v in (w.service_date, w.from_secs, w.to_secs)]
    with conn.cursor(row_factory=tuple_row) as cur:
        return cur.execute(
            f"""
            SELECT w.service_date, st.trip_id, st.stop_sequence, st.stop_id,
                   COALESCE(st.arrival_secs, st.departure_secs) - w.from_secs,
                   COALESCE(st.departure_secs, st.arrival_secs) - w.from_secs,
                   COALESCE(st.pickup_type, 0), COALESCE(st.drop_off_type, 0)
            FROM (VALUES {values}) AS w(service_date, from_secs, to_secs)
            JOIN service_dates sd ON sd.service_date = w.service_date
            JOIN trips t ON t.service_id = sd.service_id
            JOIN stop_times st ON st.trip_id = t.trip_id
            WHERE st.departure_secs >= w.from_secs AND st.departure_secs < w.to_secs
            """,
            params,
        ).fetchall()


def trip_details(conn: Connection, trip_ids: list[str]) -> dict[str, dict]:
    """Line number, colour and destination of the trips used in the journeys."""
    if not trip_ids:
        return {}
    rows = conn.execute(
        """
        SELECT t.trip_id, t.headsign, t.wheelchair_accessible,
               r.route_id, r.short_name, r.mode, r.color, r.text_color
        FROM trips t
        JOIN routes r ON r.route_id = t.route_id
        WHERE t.trip_id = ANY(%s)
        """,
        (trip_ids,),
    ).fetchall()
    return {row["trip_id"]: row for row in rows}


def latest_import(conn: Connection):
    """Changes whenever a new timetable is imported (used to refresh cached data)."""
    return conn.execute("SELECT max(imported_at) AS at FROM feed_info").fetchone()["at"]
