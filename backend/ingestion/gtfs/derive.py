"""Derived tables, computed once per import so that API requests stay fast."""

import logging

import psycopg

logger = logging.getLogger(__name__)

# ~2 m tolerance: removes redundant shape points without visibly changing the lines.
ROUTE_SIMPLIFY_TOLERANCE_DEG = 0.00002

BUILD_SERVICE_DATES = [
    # 1) Regular weekly patterns from calendar.txt (empty for BKK today).
    """
    INSERT INTO service_dates (service_date, service_id)
    SELECT day::date, c.service_id
    FROM calendar c,
         generate_series(c.start_date, c.end_date, interval '1 day') AS day
    WHERE CASE extract(isodow FROM day)
            WHEN 1 THEN c.monday   WHEN 2 THEN c.tuesday  WHEN 3 THEN c.wednesday
            WHEN 4 THEN c.thursday WHEN 5 THEN c.friday   WHEN 6 THEN c.saturday
            ELSE c.sunday
          END
    ON CONFLICT DO NOTHING
    """,
    # 2) Dates explicitly added by calendar_dates.txt.
    """
    INSERT INTO service_dates (service_date, service_id)
    SELECT date, service_id FROM calendar_dates WHERE exception_type = 1
    ON CONFLICT DO NOTHING
    """,
    # 3) Dates explicitly removed by calendar_dates.txt.
    """
    DELETE FROM service_dates sd
    USING calendar_dates cd
    WHERE cd.exception_type = 2
      AND sd.service_id = cd.service_id
      AND sd.service_date = cd.date
    """,
]

BUILD_ROUTE_STOPS = """
    INSERT INTO route_stops (stop_id, route_id)
    SELECT DISTINCT st.stop_id, t.route_id
    FROM stop_times st
    JOIN trips t ON t.trip_id = st.trip_id
"""

BUILD_STOP_MODES = [
    """
    UPDATE stops s
    SET modes = m.modes
    FROM (
        SELECT rs.stop_id, array_agg(DISTINCT r.mode ORDER BY r.mode) AS modes
        FROM route_stops rs
        JOIN routes r ON r.route_id = rs.route_id
        GROUP BY rs.stop_id
    ) m
    WHERE s.stop_id = m.stop_id
    """,
    # Stations inherit the modes of their platforms.
    """
    UPDATE stops s
    SET modes = m.modes
    FROM (
        SELECT child.parent_station AS stop_id,
               array_agg(DISTINCT mode ORDER BY mode) AS modes
        FROM stops child, unnest(child.modes) AS mode
        WHERE child.parent_station IS NOT NULL
        GROUP BY child.parent_station
    ) m
    WHERE s.stop_id = m.stop_id AND s.location_type = 1
    """,
]

# For every route and direction, draw the shape used by the most trips.
BUILD_ROUTE_GEOMETRY = """
    WITH shape_usage AS (
        SELECT route_id, COALESCE(direction_id, 0) AS direction_id, shape_id,
               count(*) AS trip_count
        FROM trips
        WHERE shape_id IS NOT NULL
        GROUP BY route_id, COALESCE(direction_id, 0), shape_id
    ),
    main_shapes AS (
        SELECT DISTINCT ON (route_id, direction_id) route_id, shape_id
        FROM shape_usage
        ORDER BY route_id, direction_id, trip_count DESC, shape_id
    )
    UPDATE routes r
    SET geom = g.geom
    FROM (
        SELECT m.route_id,
               ST_Multi(ST_Collect(ST_SimplifyPreserveTopology(s.geom, %(tolerance)s)))
                   ::geometry(MultiLineString, 4326) AS geom
        FROM main_shapes m
        JOIN shapes s ON s.shape_id = m.shape_id
        GROUP BY m.route_id
    ) g
    WHERE r.route_id = g.route_id
"""


def build_derived_tables(cur: psycopg.Cursor) -> dict[str, int]:
    counts: dict[str, int] = {}

    for statement in BUILD_SERVICE_DATES:
        cur.execute(statement)
    cur.execute("SELECT count(*) FROM service_dates")
    counts["service_dates"] = cur.fetchone()[0]

    cur.execute(BUILD_ROUTE_STOPS)
    counts["route_stops"] = cur.rowcount

    for statement in BUILD_STOP_MODES:
        cur.execute(statement)

    cur.execute(BUILD_ROUTE_GEOMETRY, {"tolerance": ROUTE_SIMPLIFY_TOLERANCE_DEG})
    counts["routes_with_geometry"] = cur.rowcount

    logger.info("Derived tables: %s", counts)
    return counts
