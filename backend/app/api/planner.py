"""GET /api/plan — public-transport journeys from A to B (scheduled timetable)."""

from datetime import date, datetime, time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg import Connection

from app.api.deps import get_settings, local_now, local_timezone
from app.config import BUDAPEST_BOUNDS, Settings
from app.db import get_connection
from app.schemas.planner import PlanResponse
from app.services.planner import Point, distance_m, plan

router = APIRouter(tags=["route planner"])

ConnDep = Annotated[Connection, Depends(get_connection)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def parse_point(raw: str, name: str | None, label: str) -> Point:
    try:
        lat, lon = (float(part) for part in raw.split(","))
    except ValueError as exc:
        raise HTTPException(422, f"'{label}' must be 'latitude,longitude'") from exc
    b = BUDAPEST_BOUNDS
    if not (b["min_lat"] <= lat <= b["max_lat"] and b["min_lon"] <= lon <= b["max_lon"]):
        raise HTTPException(422, f"'{label}' must be within the Budapest area")
    return Point(lat, lon, (name or "").strip() or f"{lat:.5f}, {lon:.5f}")


@router.get("/plan", response_model=PlanResponse)
def get_plan(
    conn: ConnDep,
    settings: SettingsDep,
    from_: Annotated[
        str, Query(alias="from", description="Start as 'lat,lon'", examples=["47.4979,19.0546"])
    ],
    to: Annotated[str, Query(description="Destination as 'lat,lon'", examples=["47.5030,19.1370"])],
    from_name: Annotated[str | None, Query(max_length=120)] = None,
    to_name: Annotated[str | None, Query(max_length=120)] = None,
    date_: Annotated[
        date | None, Query(alias="date", description="YYYY-MM-DD (default today)")
    ] = None,
    time_: Annotated[
        str | None,
        Query(
            alias="time", pattern=r"^\d{2}:\d{2}$", description="HH:MM Budapest time (default now)"
        ),
    ] = None,
) -> PlanResponse:
    """Up to three public-transport journeys, plus a walking option for short distances.

    Based on the **scheduled** BKK timetable: delays and cancellations are not included.
    """
    origin = parse_point(from_, from_name, "from")
    destination = parse_point(to, to_name, "to")
    if distance_m(origin.lat, origin.lon, destination.lat, destination.lon) < 30:
        raise HTTPException(422, "Start and destination are the same place")

    tz = local_timezone(settings)
    now = local_now(settings).replace(second=0, microsecond=0)
    if time_ is not None:
        hour, minute = (int(x) for x in time_.split(":"))
        if hour > 23 or minute > 59:
            raise HTTPException(422, "time must be a valid HH:MM")
        at = datetime.combine(date_ or now.date(), time(hour, minute), tzinfo=tz)
    elif date_ is not None and date_ != now.date():
        at = datetime.combine(date_, time(0, 0), tzinfo=tz)
    else:
        at = now
    return plan(conn, origin, destination, at, tz)
