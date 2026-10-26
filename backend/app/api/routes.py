from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response
from psycopg import Connection

from app.api.deps import get_settings, local_now, parse_csv_param, parse_mode_param
from app.config import Settings
from app.db import get_connection
from app.repositories import routes as repo
from app.schemas.transit import RouteDetail, RouteDirection, RouteStop, RouteSummary

router = APIRouter(prefix="/routes", tags=["routes"])

ConnDep = Annotated[Connection, Depends(get_connection)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


@router.get("", response_model=list[RouteSummary])
def list_routes(
    conn: ConnDep,
    mode: Annotated[str | None, Query(description="Comma-separated modes, e.g. tram,metro")] = None,
    q: Annotated[str | None, Query(min_length=1, max_length=100, description="Name search")] = None,
) -> list[RouteSummary]:
    """All routes (no geometry), ordered like BKK's official line list."""
    return [RouteSummary(**row) for row in repo.list_routes(conn, parse_mode_param(mode), q)]


# Declared before /{route_id} so that "geometry" is not mistaken for a route id.
@router.get(
    "/geometry",
    response_class=Response,
    responses={
        200: {
            "content": {"application/geo+json": {}},
            "description": "GeoJSON FeatureCollection of MultiLineString features",
        }
    },
)
def routes_geometry(
    conn: ConnDep,
    mode: Annotated[str | None, Query(description="Comma-separated modes")] = None,
    route_id: Annotated[str | None, Query(description="Comma-separated route ids")] = None,
) -> Response:
    """Route lines for the map (main pattern per direction, simplified)."""
    geojson = repo.routes_geojson(conn, parse_mode_param(mode), parse_csv_param(route_id))
    return Response(geojson, media_type="application/geo+json")


@router.get("/{route_id}", response_model=RouteDetail)
def get_route(
    route_id: Annotated[str, Path(min_length=1, max_length=64)],
    conn: ConnDep,
    settings: SettingsDep,
) -> RouteDetail:
    """Route details: directions with their ordered stops, today's trip count, geometry."""
    route = repo.get_route(conn, route_id)
    if route is None:
        raise HTTPException(404, f"Route '{route_id}' not found")

    directions: dict[int, RouteDirection] = {}
    for row in repo.route_direction_stops(conn, route_id):
        direction = directions.setdefault(
            row["direction_id"],
            RouteDirection(direction_id=row["direction_id"], headsign=row["headsign"], stops=[]),
        )
        direction.stops.append(RouteStop(**row))

    return RouteDetail(
        **route,
        trips_today=repo.count_trips_on(conn, route_id, local_now(settings).date()),
        directions=list(directions.values()),
    )
