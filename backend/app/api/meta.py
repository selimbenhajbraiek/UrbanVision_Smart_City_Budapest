from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from psycopg import Connection

from app.api.deps import get_settings, local_now
from app.config import Settings
from app.data_sources import DATA_SOURCES
from app.db import get_connection
from app.repositories import meta as repo
from app.schemas.meta import FeedInfo, MetaResponse, RealtimeStatus, StatsResponse

router = APIRouter(tags=["meta"])

ConnDep = Annotated[Connection, Depends(get_connection)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def feed_info(conn: Connection, today: date) -> FeedInfo | None:
    row = repo.latest_feed(conn)
    if row is None:
        return None
    covers_today = bool(
        row["valid_from"] and row["valid_to"] and row["valid_from"] <= today <= row["valid_to"]
    )
    return FeedInfo(**row, covers_today=covers_today)


def realtime_status(request: Request) -> RealtimeStatus:
    provider = request.app.state.realtime
    return RealtimeStatus(
        enabled=provider.enabled, provider=provider.name, message=provider.status_message
    )


@router.get("/meta", response_model=MetaResponse)
def get_meta(request: Request, conn: ConnDep, settings: SettingsDep) -> MetaResponse:
    """Timetable validity, real-time status and data-source attributions."""
    return MetaResponse(
        app="UrbanVision",
        version=request.app.version,
        timezone=settings.timezone,
        feed=feed_info(conn, local_now(settings).date()),
        realtime=realtime_status(request),
        data_sources=DATA_SOURCES,
    )


@router.get("/stats", response_model=StatsResponse)
def get_stats(conn: ConnDep, settings: SettingsDep) -> StatsResponse:
    """Key figures for the dashboard."""
    today = local_now(settings).date()
    counts = repo.transit_counts(conn, today)
    by_mode = repo.routes_by_mode(conn)
    return StatsResponse(
        **counts,
        transport_modes=len(by_mode),
        routes_by_mode=by_mode,
        stops_by_mode=repo.stops_by_mode(conn),
        feed=feed_info(conn, today),
    )
