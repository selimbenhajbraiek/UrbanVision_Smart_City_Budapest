"""Timetable lookups used to explain live vehicles ("tram 4 towards Széll Kálmán tér")."""

from psycopg import Connection


def trip_context(conn: Connection, trip_ids: list[str]) -> dict[str, dict]:
    """Route, headsign and final stop of each trip found in the imported timetable.

    Live trips from a newer BKK timetable than the imported one are simply not found.
    """
    if not trip_ids:
        return {}
    rows = conn.execute(
        """
        SELECT t.trip_id, t.route_id, t.headsign, t.direction_id, last_stop.name AS final_stop
        FROM trips t
        LEFT JOIN LATERAL (
            SELECT s.name
            FROM stop_times st
            JOIN stops s ON s.stop_id = st.stop_id
            WHERE st.trip_id = t.trip_id
            ORDER BY st.stop_sequence DESC
            LIMIT 1
        ) last_stop ON TRUE
        WHERE t.trip_id = ANY(%s)
        """,
        (trip_ids,),
    ).fetchall()
    return {row["trip_id"]: row for row in rows}


def stop_names(conn: Connection, stop_ids: list[str]) -> dict[str, str]:
    if not stop_ids:
        return {}
    rows = conn.execute(
        "SELECT stop_id, name FROM stops WHERE stop_id = ANY(%s)", (stop_ids,)
    ).fetchall()
    return {row["stop_id"]: row["name"] for row in rows}
