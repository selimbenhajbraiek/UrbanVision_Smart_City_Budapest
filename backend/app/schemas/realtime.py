from datetime import datetime

from pydantic import BaseModel

from app.schemas import DataStatus


class Vehicle(BaseModel):
    vehicle_id: str
    label: str | None  # BKK's own destination label
    license_plate: str | None
    wheelchair_accessible: bool | None
    in_service: bool  # False = no trip assigned (depot, positioning run)
    trip_id: str | None
    trip_in_timetable: bool  # False if the trip is not in the imported GTFS feed
    route_id: str | None
    route_short_name: str | None
    route_description: str | None
    mode: str | None
    color: str | None
    text_color: str | None
    headsign: str | None  # where the vehicle is going
    final_stop: str | None
    next_stop_id: str | None
    next_stop_name: str | None
    current_status: str | None  # in_transit_to | stopped_at | incoming_at
    latitude: float
    longitude: float
    bearing: float | None
    speed_kmh: float | None
    timestamp: datetime | None


class VehiclesResponse(BaseModel):
    data_status: DataStatus = "realtime"
    provider: str
    feed_timestamp: datetime | None
    fetched_at: datetime
    vehicles: list[Vehicle]


class Alert(BaseModel):
    alert_id: str
    header: str | None
    description: str | None
    url: str | None
    route_ids: list[str]
    stop_ids: list[str]
    active_from: datetime | None
    active_until: datetime | None


class AlertsResponse(BaseModel):
    data_status: DataStatus = "realtime"
    provider: str
    feed_timestamp: datetime | None
    fetched_at: datetime
    alerts: list[Alert]
