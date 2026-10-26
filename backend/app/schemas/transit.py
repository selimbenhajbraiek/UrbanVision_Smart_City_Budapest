from datetime import date, datetime
from typing import Any

from pydantic import BaseModel

from app.schemas import DataStatus


class RouteSummary(BaseModel):
    route_id: str
    short_name: str | None
    long_name: str | None
    description: str | None
    mode: str
    route_type: int
    color: str | None
    text_color: str | None
    agency_id: str | None


class StopSummary(BaseModel):
    stop_id: str
    name: str
    latitude: float
    longitude: float
    modes: list[str]
    distance_m: float | None = None


class StopDetail(BaseModel):
    stop_id: str
    stop_code: str | None
    name: str
    latitude: float
    longitude: float
    location_type: int
    parent_station: str | None
    wheelchair_boarding: int | None
    modes: list[str]
    routes: list[RouteSummary]
    nearby_platforms: list[StopSummary]


class RouteStop(BaseModel):
    sequence: int
    stop_id: str
    name: str
    latitude: float
    longitude: float


class RouteDirection(BaseModel):
    direction_id: int
    headsign: str | None
    stops: list[RouteStop]


class RouteDetail(RouteSummary):
    agency_name: str | None
    trips_today: int
    directions: list[RouteDirection]
    geometry: dict[str, Any] | None  # GeoJSON MultiLineString


class Departure(BaseModel):
    trip_id: str
    route_id: str
    route_short_name: str | None
    mode: str
    color: str | None
    text_color: str | None
    headsign: str | None
    service_date: date
    scheduled_time: str  # original GTFS value, may exceed 24:00:00
    departure_time: datetime
    minutes_until: int
    wheelchair_accessible: bool | None


class DeparturesResponse(BaseModel):
    stop_id: str
    stop_name: str
    requested_at: datetime
    window_minutes: int
    data_status: DataStatus = "scheduled"
    schedule_available: bool
    notice: str | None
    departures: list[Departure]


class StopSearchResult(BaseModel):
    stop_id: str
    name: str
    latitude: float
    longitude: float
    modes: list[str]
    platform_count: int


class SearchResponse(BaseModel):
    query: str
    stops: list[StopSearchResult]
    routes: list[RouteSummary]
