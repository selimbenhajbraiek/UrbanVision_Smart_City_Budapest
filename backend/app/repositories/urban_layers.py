from psycopg import Connection

from app.repositories import BBOX_CONDITION, BBox


def layer_imports(conn: Connection) -> dict[str, dict]:
    rows = conn.execute(
        "SELECT category, feature_count, osm_data_timestamp, imported_at FROM urban_layer_imports"
    ).fetchall()
    return {row["category"]: row for row in rows}


def layer_geojson(
    conn: Connection, layer_id: str, popup_tags: tuple[str, ...], bbox: BBox | None
) -> str:
    conditions = ["category = %(layer_id)s"]
    params: dict = {"layer_id": layer_id, "popup_tags": list(popup_tags)}
    if bbox:
        conditions.append(BBOX_CONDITION)
        params.update(bbox.as_params())
    sql = f"""
        SELECT json_build_object(
            'type', 'FeatureCollection',
            'features', COALESCE(json_agg(json_build_object(
                'type', 'Feature',
                'id', osm_type || '/' || osm_id,
                'geometry', ST_AsGeoJSON(geom, 6)::json,
                'properties', json_build_object(
                    'name', name,
                    'operator', operator,
                    'osm_url', 'https://www.openstreetmap.org/' || osm_type || '/' || osm_id,
                    -- only the tags that are useful in a popup
                    'details', (SELECT COALESCE(jsonb_object_agg(key, value), '{{}}'::jsonb)
                                FROM jsonb_each_text(tags)
                                WHERE key = ANY(%(popup_tags)s))
                )
            )), '[]'::json)
        )::text AS geojson
        FROM urban_pois
        WHERE {" AND ".join(conditions)}
    """
    return conn.execute(sql, params).fetchone()["geojson"]
