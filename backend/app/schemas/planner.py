"""Route planner responses (scheduled timetable: no live delays)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas import DataStatus


class Place(BaseModel):
    name: str
    latitude: float
    longitude: float
    stop_id: str | None = None


class LegRoute(BaseModel):
    route_id: str
    short_name: str | None
    mode: str
    color: str | None
    text_color: str | None


class Leg(BaseModel):
    """One step of a journey: walking, or riding one vehicle."""

    kind: Literal["walk", "transit"]
    start: Place
    end: Place
    departure: datetime
    arrival: datetime
    duration_minutes: int
    distance_m: int | None = Field(None, description="Walk legs only")
    route: LegRoute | None = Field(None, description="Transit legs only")
    headsign: str | None = None
    trip_id: str | None = None
    stop_count: int | None = Field(None, description="Stops travelled (boarding stop not counted)")
    intermediate_stops: list[Place] = []
    wheelchair_accessible: bool | None = None
    geometry: list[tuple[float, float]] = Field(
        description="[longitude, latitude] points to draw the leg on the map"
    )


class Journey(BaseModel):
    departure: datetime
    arrival: datetime
    duration_minutes: int
    transfers: int
    walking_minutes: int
    walking_m: int
    legs: list[Leg]


class PlanResponse(BaseModel):
    origin: Place
    destination: Place
    requested_at: datetime
    data_status: DataStatus = "scheduled"
    schedule_available: bool
    notice: str | None
    journeys: list[Journey]
