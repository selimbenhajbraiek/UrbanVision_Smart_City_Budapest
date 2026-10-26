from datetime import date

from psycopg import Connection


def latest_feed(conn: Connection) -> dict | None:
    return conn.execute(
        """
        SELECT publisher_name, feed_version, feed_start_date AS valid_from,
               feed_end_date AS valid_to, imported_at
        FROM feed_info
        ORDER BY imported_at DESC
        LIMIT 1
        """
    ).fetchone()


def transit_counts(conn: Connection, today: date) -> dict:
    return conn.execute(
        """
        SELECT
          (SELECT count(*) FROM stops WHERE location_type = 0 AND cardinality(modes) > 0)
              AS stops,
          (SELECT count(*) FROM stops WHERE location_type = 1) AS stations,
          (SELECT count(*) FROM routes) AS routes,
          (SELECT count(*) FROM trips) AS trips,
          (SELECT count(*) FROM trips t
             JOIN service_dates sd ON sd.service_id = t.service_id
            WHERE sd.service_date = %s) AS trips_today,
          (SELECT count(*) FROM urban_pois) AS urban_features
        """,
        (today,),
    ).fetchone()


def routes_by_mode(conn: Connection) -> dict[str, int]:
    rows = conn.execute("SELECT mode, count(*) AS n FROM routes GROUP BY mode").fetchall()
    return {row["mode"]: row["n"] for row in rows}


def stops_by_mode(conn: Connection) -> dict[str, int]:
    rows = conn.execute(
        """
        SELECT mode, count(*) AS n
        FROM stops, unnest(modes) AS mode
        WHERE location_type = 0
        GROUP BY mode
        """
    ).fetchall()
    return {row["mode"]: row["n"] for row in rows}
