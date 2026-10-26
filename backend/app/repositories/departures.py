from dataclasses import dataclass
from datetime import date

from psycopg import Connection


@dataclass(frozen=True)
class ServiceWindow:
    """Search window expressed in GTFS seconds relative to one service date."""

    service_date: date
    from_secs: int
    to_secs: int


def scheduled_departures(
    conn: Connection, stop_id: str, windows: list[ServiceWindow], limit: int
) -> list[dict]:
    """Departures from a stop (or all platforms of a station) inside the given windows.

    Several windows are needed because a departure at 00:30 can belong to *yesterday's*
    service (GTFS time 24:30:00) as well as today's. `seconds_from_request` lets us sort
    departures from different service days on one timeline.
    """
    values = ", ".join(["(%s::date, %s::int, %s::int)"] * len(windows))
    params: list = [v for w in windows for v in (w.service_date, w.from_secs, w.to_secs)]
    params += [stop_id, stop_id, limit]
    return conn.execute(
        f"""
        SELECT st.trip_id, st.departure_secs, w.service_date,
               st.departure_secs - w.from_secs AS seconds_from_request,
               COALESCE(st.stop_headsign, t.headsign) AS headsign,
               t.wheelchair_accessible,
               r.route_id, r.short_name AS route_short_name, r.mode, r.color, r.text_color
        FROM (VALUES {values}) AS w(service_date, from_secs, to_secs)
        JOIN stop_times st
          ON st.departure_secs >= w.from_secs AND st.departure_secs < w.to_secs
        JOIN trips t ON t.trip_id = st.trip_id
        JOIN service_dates sd
          ON sd.service_id = t.service_id AND sd.service_date = w.service_date
        JOIN routes r ON r.route_id = t.route_id
        WHERE st.stop_id IN (
                SELECT %s UNION ALL SELECT stop_id FROM stops WHERE parent_station = %s)
          AND COALESCE(st.pickup_type, 0) <> 1          -- 1 = no pickup at this stop
          AND EXISTS (                                  -- skip arrivals at the last stop
                SELECT 1 FROM stop_times nxt
                WHERE nxt.trip_id = st.trip_id AND nxt.stop_sequence > st.stop_sequence)
        ORDER BY seconds_from_request, r.sort_order NULLS LAST
        LIMIT %s
        """,
        params,
    ).fetchall()


def has_service_on(conn: Connection, service_date: date) -> bool:
    row = conn.execute(
        "SELECT EXISTS (SELECT 1 FROM service_dates WHERE service_date = %s) AS ok",
        (service_date,),
    ).fetchone()
    return row["ok"]
