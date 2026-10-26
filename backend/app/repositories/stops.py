from psycopg import Connection

from app.repositories import BBOX_CONDITION, BBox, like_pattern

# Strips the "M"/"H"/"M+H" interchange suffix and anything after a comma, so that
# "Deák Ferenc tér M" and "Deák Ferenc tér" are recognised as the same place.
BASE_NAME_SQL = r"regexp_replace(split_part({col}, ',', 1), '\s+(M\+H|M|H)$', '')"


def stops_geojson(conn: Connection, bbox: BBox | None, modes: list[str] | None, limit: int) -> str:
    # Only real boarding points that are served by at least one route are mapped.
    conditions = ["location_type = 0", "cardinality(modes) > 0"]
    params: dict = {"limit": limit}
    if bbox:
        conditions.append(BBOX_CONDITION)
        params.update(bbox.as_params())
    if modes:
        conditions.append("modes && %(modes)s::text[]")
        params["modes"] = modes
    sql = f"""
        SELECT json_build_object(
            'type', 'FeatureCollection',
            'features', COALESCE(json_agg(json_build_object(
                'type', 'Feature',
                'id', stop_id,
                'geometry', ST_AsGeoJSON(geom, 6)::json,
                'properties', json_build_object(
                    'stop_id', stop_id, 'name', name, 'stop_code', stop_code, 'modes', modes)
            )), '[]'::json)
        )::text AS geojson
        FROM (
            SELECT stop_id, name, stop_code, modes, geom
            FROM stops
            WHERE {" AND ".join(conditions)}
            ORDER BY stop_id
            LIMIT %(limit)s
        ) s
    """
    return conn.execute(sql, params).fetchone()["geojson"]


def get_stop(conn: Connection, stop_id: str) -> dict | None:
    return conn.execute(
        """
        SELECT stop_id, stop_code, name, ST_Y(geom) AS latitude, ST_X(geom) AS longitude,
               location_type, parent_station, wheelchair_boarding, modes
        FROM stops WHERE stop_id = %s
        """,
        (stop_id,),
    ).fetchone()


def routes_serving_stop(conn: Connection, stop_id: str) -> list[dict]:
    """Routes calling at this stop, or at any platform of this station."""
    return conn.execute(
        """
        SELECT DISTINCT r.route_id, r.short_name, r.long_name, r.description, r.mode,
               r.route_type, r.color, r.text_color, r.agency_id, r.sort_order
        FROM route_stops rs
        JOIN routes r ON r.route_id = rs.route_id
        WHERE rs.stop_id = %(stop_id)s
           OR rs.stop_id IN (SELECT stop_id FROM stops WHERE parent_station = %(stop_id)s)
        ORDER BY r.sort_order NULLS LAST, r.short_name
        """,
        {"stop_id": stop_id},
    ).fetchall()


def nearby_platforms(conn: Connection, stop_id: str, radius_m: int = 300) -> list[dict]:
    """Other platforms of the same interchange (same station, or same base name nearby)."""
    base_me = BASE_NAME_SQL.format(col="name")
    base_other = BASE_NAME_SQL.format(col="s.name")
    return conn.execute(
        f"""
        WITH me AS (
            SELECT stop_id, geom, parent_station, {base_me} AS base_name
            FROM stops WHERE stop_id = %(stop_id)s
        )
        SELECT s.stop_id, s.name, ST_Y(s.geom) AS latitude, ST_X(s.geom) AS longitude,
               s.modes, round(ST_Distance(s.geom::geography, me.geom::geography)) AS distance_m
        FROM stops s, me
        WHERE s.stop_id <> me.stop_id
          AND s.location_type = 0
          AND cardinality(s.modes) > 0
          AND s.geom && ST_Expand(me.geom, 0.01)
          AND ST_DWithin(s.geom::geography, me.geom::geography, %(radius)s)
          AND ((me.parent_station IS NOT NULL AND s.parent_station = me.parent_station)
               OR {base_other} = me.base_name)
        ORDER BY distance_m
        LIMIT 20
        """,
        {"stop_id": stop_id, "radius": radius_m},
    ).fetchall()


def search_stops(conn: Connection, query: str, limit: int) -> list[dict]:
    """Accent-insensitive name search. Platforms with the same name within ~1 km are grouped."""
    return conn.execute(
        """
        WITH matches AS (
            SELECT stop_id, name, geom, modes, ST_SnapToGrid(geom, 0.01) AS cell
            FROM stops
            WHERE location_type = 0
              AND cardinality(modes) > 0
              AND unaccent(name) ILIKE unaccent(%(pattern)s)
        ),
        groups AS (
            SELECT min(stop_id) AS stop_id, name, cell,
                   avg(ST_Y(geom)) AS latitude, avg(ST_X(geom)) AS longitude,
                   count(*) AS platform_count
            FROM matches
            GROUP BY name, cell
        )
        SELECT g.stop_id, g.name, g.latitude, g.longitude, g.platform_count,
               ARRAY(SELECT DISTINCT mode
                     FROM matches m, unnest(m.modes) AS mode
                     WHERE m.name = g.name AND m.cell = g.cell
                     ORDER BY mode) AS modes
        FROM groups g
        ORDER BY (unaccent(g.name) ILIKE unaccent(%(prefix)s)) DESC, g.platform_count DESC, g.name
        LIMIT %(limit)s
        """,
        {"pattern": like_pattern(query), "prefix": like_pattern(query)[1:], "limit": limit},
    ).fetchall()
