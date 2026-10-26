from datetime import date

from psycopg import Connection

from app.repositories import like_pattern

ROUTE_COLUMNS = (
    "r.route_id, r.short_name, r.long_name, r.description, r.mode, r.route_type, "
    "r.color, r.text_color, r.agency_id"
)


def list_routes(conn: Connection, modes: list[str] | None, query: str | None) -> list[dict]:
    conditions, params = ["TRUE"], {}
    if modes:
        conditions.append("r.mode = ANY(%(modes)s)")
        params["modes"] = modes
    if query:
        conditions.append(
            "(r.short_name ILIKE %(prefix)s OR unaccent(COALESCE(r.long_name, '') || ' ' ||"
            " COALESCE(r.description, '')) ILIKE unaccent(%(pattern)s))"
        )
        params["pattern"] = like_pattern(query)
        params["prefix"] = like_pattern(query)[1:]
        params["exact"] = query
    order = "(r.short_name ILIKE %(exact)s) DESC, " if query else ""
    return conn.execute(
        f"""
        SELECT {ROUTE_COLUMNS}
        FROM routes r
        WHERE {" AND ".join(conditions)}
        ORDER BY {order}r.sort_order NULLS LAST, r.short_name
        """,
        params,
    ).fetchall()


def get_route(conn: Connection, route_id: str) -> dict | None:
    return conn.execute(
        f"""
        SELECT {ROUTE_COLUMNS}, a.name AS agency_name,
               ST_AsGeoJSON(r.geom, 6)::json AS geometry
        FROM routes r
        LEFT JOIN agencies a ON a.agency_id = r.agency_id
        WHERE r.route_id = %s
        """,
        (route_id,),
    ).fetchone()


def count_trips_on(conn: Connection, route_id: str, service_date: date) -> int:
    return conn.execute(
        """
        SELECT count(*) AS n
        FROM trips t
        JOIN service_dates sd ON sd.service_id = t.service_id AND sd.service_date = %s
        WHERE t.route_id = %s
        """,
        (service_date, route_id),
    ).fetchone()["n"]


def route_direction_stops(conn: Connection, route_id: str) -> list[dict]:
    """Ordered stops of the most common trip pattern in each direction."""
    return conn.execute(
        """
        WITH patterns AS (
            SELECT COALESCE(direction_id, 0) AS direction_id, shape_id,
                   count(*) AS trip_count, min(trip_id) AS sample_trip_id,
                   mode() WITHIN GROUP (ORDER BY headsign) AS headsign
            FROM trips
            WHERE route_id = %s
            GROUP BY COALESCE(direction_id, 0), shape_id
        ),
        main AS (
            SELECT DISTINCT ON (direction_id) direction_id, sample_trip_id, headsign
            FROM patterns
            ORDER BY direction_id, trip_count DESC, sample_trip_id
        )
        SELECT m.direction_id, m.headsign, st.stop_sequence AS sequence, s.stop_id, s.name,
               ST_Y(s.geom) AS latitude, ST_X(s.geom) AS longitude
        FROM main m
        JOIN stop_times st ON st.trip_id = m.sample_trip_id
        JOIN stops s ON s.stop_id = st.stop_id
        ORDER BY m.direction_id, st.stop_sequence
        """,
        (route_id,),
    ).fetchall()


def routes_geojson(conn: Connection, modes: list[str] | None, route_ids: list[str] | None) -> str:
    conditions, params = ["geom IS NOT NULL"], {}
    if modes:
        conditions.append("mode = ANY(%(modes)s)")
        params["modes"] = modes
    if route_ids:
        conditions.append("route_id = ANY(%(route_ids)s)")
        params["route_ids"] = route_ids
    sql = f"""
        SELECT json_build_object(
            'type', 'FeatureCollection',
            'features', COALESCE(json_agg(json_build_object(
                'type', 'Feature',
                'id', route_id,
                'geometry', ST_AsGeoJSON(geom, 5)::json,
                'properties', json_build_object(
                    'route_id', route_id, 'short_name', short_name, 'mode', mode,
                    'color', color, 'text_color', text_color, 'description', description)
            ) ORDER BY sort_order DESC NULLS FIRST), '[]'::json)
        )::text AS geojson
        FROM routes
        WHERE {" AND ".join(conditions)}
    """
    return conn.execute(sql, params).fetchone()["geojson"]


def route_styles(conn: Connection, route_ids: list[str]) -> dict[str, dict]:
    """Short name / mode / colour per route, used to decorate real-time vehicles."""
    if not route_ids:
        return {}
    rows = conn.execute(
        "SELECT route_id, short_name, mode, color, text_color, description FROM routes"
        " WHERE route_id = ANY(%s)",
        (route_ids,),
    ).fetchall()
    return {row["route_id"]: row for row in rows}
