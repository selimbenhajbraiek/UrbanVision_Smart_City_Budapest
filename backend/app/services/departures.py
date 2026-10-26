from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from psycopg import Connection

from app.repositories import departures as repo
from app.repositories.departures import ServiceWindow
from app.schemas.transit import Departure, DeparturesResponse
from app.services.schedule_time import (
    format_gtfs_seconds,
    schedule_to_datetime,
    seconds_since_service_start,
)


def build_windows(at: datetime, minutes: int, tz: ZoneInfo) -> list[ServiceWindow]:
    """A time window can contain trips of three service days: yesterday's late-night trips
    (GTFS times > 24:00), today's, and — if the window passes midnight — tomorrow's."""
    windows = []
    for day_offset in (-1, 0, 1):
        service_date = at.date() + timedelta(days=day_offset)
        start = seconds_since_service_start(at, service_date, tz)
        windows.append(ServiceWindow(service_date, start, start + minutes * 60))
    return windows


def get_departures(
    conn: Connection,
    stop: dict,
    at: datetime,
    minutes: int,
    limit: int,
    tz: ZoneInfo,
) -> DeparturesResponse:
    rows = repo.scheduled_departures(conn, stop["stop_id"], build_windows(at, minutes, tz), limit)
    departures = [
        Departure(
            trip_id=row["trip_id"],
            route_id=row["route_id"],
            route_short_name=row["route_short_name"],
            mode=row["mode"],
            color=row["color"],
            text_color=row["text_color"],
            headsign=row["headsign"],
            service_date=row["service_date"],
            scheduled_time=format_gtfs_seconds(row["departure_secs"]),
            departure_time=schedule_to_datetime(row["service_date"], row["departure_secs"], tz),
            minutes_until=row["seconds_from_request"] // 60,
            wheelchair_accessible=None
            if row["wheelchair_accessible"] in (None, 0)
            else row["wheelchair_accessible"] == 1,
        )
        for row in rows
    ]

    schedule_available = repo.has_service_on(conn, at.date())
    notice = None
    if not schedule_available:
        notice = (
            f"The imported timetable does not cover {at.date().isoformat()}. "
            "Import a newer BKK GTFS feed to see departures."
        )
    elif not departures:
        notice = f"No scheduled departures in the next {minutes} minutes."

    return DeparturesResponse(
        stop_id=stop["stop_id"],
        stop_name=stop["name"],
        requested_at=at,
        window_minutes=minutes,
        schedule_available=schedule_available,
        notice=notice,
        departures=departures,
    )
