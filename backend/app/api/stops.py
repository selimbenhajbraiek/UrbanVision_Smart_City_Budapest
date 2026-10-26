from datetime import date, datetime, time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response
from psycopg import Connection

from app.api.deps import get_settings, local_now, local_timezone, parse_bbox, parse_mode_param
from app.config import Settings
from app.db import get_connection
from app.repositories import stops as repo
from app.schemas.transit import DeparturesResponse, RouteSummary, StopDetail, StopSummary
from app.services.departures import get_departures

router = APIRouter(prefix="/stops", tags=["stops"])

ConnDep = Annotated[Connection, Depends(get_connection)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
StopId = Annotated[str, Path(min_length=1, max_length=64)]

GEOJSON_EXAMPLE = {
    200: {
        "content": {"application/geo+json": {}},
        "description": "GeoJSON FeatureCollection of Point features",
    }
}


def _get_stop_or_404(conn: Connection, stop_id: str) -> dict:
    stop = repo.get_stop(conn, stop_id)
    if stop is None:
        raise HTTPException(404, f"Stop '{stop_id}' not found")
    return stop


@router.get("", response_class=Response, responses=GEOJSON_EXAMPLE)
def list_stops(
    conn: ConnDep,
    bbox: Annotated[
        str | None,
        Query(description="minLon,minLat,maxLon,maxLat", examples=["19.03,47.49,19.07,47.51"]),
    ] = None,
    mode: Annotated[
        str | None,
        Query(description="Comma-separated modes, e.g. metro,tram", examples=["metro,tram"]),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=10000)] = 5000,
) -> Response:
    """Public-transport stops (boarding points served by at least one route) as GeoJSON."""
    geojson = repo.stops_geojson(conn, parse_bbox(bbox), parse_mode_param(mode), limit)
    return Response(geojson, media_type="application/geo+json")


@router.get("/{stop_id}", response_model=StopDetail)
def get_stop(stop_id: StopId, conn: ConnDep) -> StopDetail:
    """Stop details, the routes serving it and other platforms of the same interchange."""
    stop = _get_stop_or_404(conn, stop_id)
    return StopDetail(
        **stop,
        routes=[RouteSummary(**r) for r in repo.routes_serving_stop(conn, stop_id)],
        nearby_platforms=[StopSummary(**s) for s in repo.nearby_platforms(conn, stop_id)],
    )


@router.get("/{stop_id}/departures", response_model=DeparturesResponse)
def stop_departures(
    stop_id: StopId,
    conn: ConnDep,
    settings: SettingsDep,
    on_date: Annotated[
        date | None, Query(alias="date", description="YYYY-MM-DD (default today)")
    ] = None,
    at_time: Annotated[
        str | None,
        Query(
            alias="time",
            pattern=r"^([01]\d|2[0-3]):[0-5]\d$",
            description="HH:MM local time (default now)",
        ),
    ] = None,
    minutes: Annotated[int, Query(ge=1, le=1440, description="Look-ahead window")] = 120,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> DeparturesResponse:
    """**Scheduled** departures from the static BKK GTFS timetable (not real-time)."""
    stop = _get_stop_or_404(conn, stop_id)
    tz = local_timezone(settings)
    now = local_now(settings)
    requested_date = on_date or now.date()
    if at_time:
        requested_time = time.fromisoformat(at_time)
    elif requested_date == now.date():
        requested_time = now.time().replace(second=0, microsecond=0)
    else:
        requested_time = time(0, 0)
    at = datetime.combine(requested_date, requested_time, tzinfo=tz)
    return get_departures(conn, stop, at, minutes, limit, tz)
