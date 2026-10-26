from datetime import date, datetime

from pydantic import BaseModel

from app.schemas import DataStatus


class FeedInfo(BaseModel):
    publisher_name: str | None
    feed_version: str | None
    valid_from: date | None
    valid_to: date | None
    imported_at: datetime
    covers_today: bool


class DataSource(BaseModel):
    id: str
    name: str
    url: str
    provides: str
    license: str
    attribution: str
    data_status: DataStatus
    update_frequency: str


class RealtimeStatus(BaseModel):
    enabled: bool
    provider: str | None
    message: str


class MetaResponse(BaseModel):
    app: str
    version: str
    timezone: str
    feed: FeedInfo | None
    realtime: RealtimeStatus
    data_sources: list[DataSource]


class StatsResponse(BaseModel):
    stops: int
    stations: int
    routes: int
    trips: int
    trips_today: int
    transport_modes: int
    routes_by_mode: dict[str, int]
    stops_by_mode: dict[str, int]
    urban_features: int
    feed: FeedInfo | None


class HealthResponse(BaseModel):
    status: str
    database: str
    gtfs_loaded: bool


class UrbanLayerInfo(BaseModel):
    id: str
    title: str
    description: str
    feature_count: int
    imported_at: datetime | None
    osm_data_timestamp: str | None
    data_status: DataStatus = "static"
    source: str = "OpenStreetMap contributors (Overpass API)"
    license: str = "ODbL 1.0"
