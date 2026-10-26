from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class VehiclePosition:
    vehicle_id: str
    label: str | None
    trip_id: str | None
    route_id: str | None
    latitude: float
    longitude: float
    bearing: float | None
    speed_kmh: float | None
    timestamp: datetime | None
    stop_id: str | None = None  # the stop the vehicle is at or heading to
    current_status: str | None = None  # "in_transit_to" | "stopped_at" | "incoming_at"
    license_plate: str | None = None
    wheelchair_accessible: bool | None = None


@dataclass(frozen=True)
class ServiceAlert:
    alert_id: str
    header: str | None
    description: str | None
    url: str | None
    route_ids: list[str] = field(default_factory=list)
    stop_ids: list[str] = field(default_factory=list)
    active_from: datetime | None = None
    active_until: datetime | None = None


@dataclass(frozen=True)
class RealtimeSnapshot(Generic[T]):  # noqa: UP046 - keeps Python 3.11 support
    items: list[T]
    feed_timestamp: datetime | None
    fetched_at: datetime


class RealtimeProvider(ABC):
    name: str | None = None

    @property
    @abstractmethod
    def enabled(self) -> bool: ...

    @property
    @abstractmethod
    def status_message(self) -> str: ...

    @abstractmethod
    def vehicle_positions(self) -> RealtimeSnapshot[VehiclePosition]: ...

    @abstractmethod
    def alerts(self) -> RealtimeSnapshot[ServiceAlert]: ...

    def close(self) -> None:  # noqa: B027 - optional hook
        pass
