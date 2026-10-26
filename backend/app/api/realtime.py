"""Real-time endpoints. They return 503 unless BKK_API_KEY is configured."""

from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from psycopg import Connection

from app.api.deps import parse_mode_param
from app.api.meta import realtime_status
from app.db import get_connection
from app.realtime import RealtimeProvider
from app.repositories.realtime import stop_names, trip_context
from app.repositories.routes import route_styles
from app.schemas.meta import RealtimeStatus
from app.schemas.realtime import Alert, AlertsResponse, Vehicle, VehiclesResponse

router = APIRouter(prefix="/realtime", tags=["real-time"])


def _provider(request: Request) -> RealtimeProvider:
    return request.app.state.realtime


@router.get("/status", response_model=RealtimeStatus)
def status(request: Request) -> RealtimeStatus:
    return realtime_status(request)


@router.get("/vehicles", response_model=VehiclesResponse)
def vehicles(
    request: Request,
    conn: Annotated[Connection, Depends(get_connection)],
    mode: Annotated[str | None, Query(description="Comma-separated modes")] = None,
    include_idle: Annotated[
        bool, Query(description="Also return vehicles without a trip (depot, positioning)")
    ] = False,
) -> VehiclesResponse:
    """Live vehicle positions, explained with the GTFS timetable: line, headsign, next stop."""
    provider = _provider(request)
    snapshot = provider.vehicle_positions()
    modes = parse_mode_param(mode)
    live = [v for v in snapshot.items if include_idle or v.trip_id]

    trips = trip_context(conn, sorted({v.trip_id for v in live if v.trip_id}))
    route_ids = {v.route_id or trips.get(v.trip_id or "", {}).get("route_id") for v in live}
    styles = route_styles(conn, sorted(r for r in route_ids if r))
    stops = stop_names(conn, sorted({v.stop_id for v in live if v.stop_id}))

    result = []
    for vehicle in live:
        trip = trips.get(vehicle.trip_id or "", {})
        route_id = vehicle.route_id or trip.get("route_id")
        style = styles.get(route_id or "", {})
        if modes and style.get("mode") not in modes:
            continue
        result.append(
            Vehicle(
                **asdict(vehicle) | {"route_id": route_id},
                in_service=vehicle.trip_id is not None,
                trip_in_timetable=bool(trip),
                route_short_name=style.get("short_name"),
                route_description=style.get("description"),
                mode=style.get("mode"),
                color=style.get("color"),
                text_color=style.get("text_color"),
                # Timetable headsign first; BKK's label is the fallback for unknown trips.
                headsign=trip.get("headsign") or vehicle.label,
                final_stop=trip.get("final_stop"),
                next_stop_id=vehicle.stop_id,
                next_stop_name=stops.get(vehicle.stop_id or ""),
            )
        )
    return VehiclesResponse(
        provider=provider.name or "unknown",
        feed_timestamp=snapshot.feed_timestamp,
        fetched_at=snapshot.fetched_at,
        vehicles=result,
    )


@router.get("/alerts", response_model=AlertsResponse)
def alerts(request: Request) -> AlertsResponse:
    """Current service disruptions published by BKK."""
    provider = _provider(request)
    snapshot = provider.alerts()
    return AlertsResponse(
        provider=provider.name or "unknown",
        feed_timestamp=snapshot.feed_timestamp,
        fetched_at=snapshot.fetched_at,
        alerts=[Alert(**asdict(alert)) for alert in snapshot.items],
    )
