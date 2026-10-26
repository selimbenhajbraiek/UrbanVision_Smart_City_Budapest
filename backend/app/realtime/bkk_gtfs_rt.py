"""BKK FUTÁR GTFS-Realtime client (VehiclePositions.pb and Alerts.pb).

Requires a free API key from https://opendata.bkk.hu/ (the endpoints return 401 without).
"""

import logging
from datetime import UTC, datetime

import httpx
from google.protobuf.message import DecodeError
from google.transit import gtfs_realtime_pb2

from app.config import Settings
from app.errors import UpstreamServiceError
from app.services.cache import TTLCache

from .base import RealtimeProvider, RealtimeSnapshot, ServiceAlert, VehiclePosition

logger = logging.getLogger(__name__)

PREFERRED_LANGUAGES = ("en", "hu")


def _timestamp(value: int) -> datetime | None:
    return datetime.fromtimestamp(value, UTC) if value else None


def _translated(text: gtfs_realtime_pb2.TranslatedString) -> str | None:
    translations = {t.language: t.text for t in text.translation}
    for language in PREFERRED_LANGUAGES:
        if translations.get(language):
            return translations[language]
    return next(iter(translations.values()), None)


_STOP_STATUS = gtfs_realtime_pb2.VehiclePosition.VehicleStopStatus
_WHEELCHAIR = gtfs_realtime_pb2.VehicleDescriptor.WheelchairAccessible


def _wheelchair(descriptor: gtfs_realtime_pb2.VehicleDescriptor) -> bool | None:
    if not descriptor.HasField("wheelchair_accessible"):
        return None
    value = descriptor.wheelchair_accessible
    if value == _WHEELCHAIR.Value("WHEELCHAIR_ACCESSIBLE"):
        return True
    if value == _WHEELCHAIR.Value("WHEELCHAIR_INACCESSIBLE"):
        return False
    return None


def parse_vehicle_positions(payload: bytes) -> tuple[list[VehiclePosition], datetime | None]:
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(payload)
    vehicles = []
    for entity in feed.entity:
        if not entity.HasField("vehicle") or not entity.vehicle.HasField("position"):
            continue
        v = entity.vehicle
        vehicles.append(
            VehiclePosition(
                vehicle_id=v.vehicle.id or entity.id,
                label=v.vehicle.label or None,
                trip_id=v.trip.trip_id or None,
                route_id=v.trip.route_id or None,
                latitude=v.position.latitude,
                longitude=v.position.longitude,
                bearing=v.position.bearing if v.position.HasField("bearing") else None,
                speed_kmh=round(v.position.speed * 3.6, 1)
                if v.position.HasField("speed")
                else None,
                timestamp=_timestamp(v.timestamp),
                stop_id=v.stop_id or None,
                current_status=_STOP_STATUS.Name(v.current_status).lower()
                if v.HasField("current_status")
                else None,
                license_plate=v.vehicle.license_plate or None,
                wheelchair_accessible=_wheelchair(v.vehicle),
            )
        )
    return vehicles, _timestamp(feed.header.timestamp)


def parse_alerts(payload: bytes) -> tuple[list[ServiceAlert], datetime | None]:
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(payload)
    alerts = []
    for entity in feed.entity:
        if not entity.HasField("alert"):
            continue
        a = entity.alert
        period = a.active_period[0] if a.active_period else None
        alerts.append(
            ServiceAlert(
                alert_id=entity.id,
                header=_translated(a.header_text),
                description=_translated(a.description_text),
                url=_translated(a.url),
                route_ids=sorted({e.route_id for e in a.informed_entity if e.route_id}),
                stop_ids=sorted({e.stop_id for e in a.informed_entity if e.stop_id}),
                active_from=_timestamp(period.start) if period else None,
                active_until=_timestamp(period.end) if period else None,
            )
        )
    return alerts, _timestamp(feed.header.timestamp)


class BkkGtfsRealtimeProvider(RealtimeProvider):
    name = "BKK FUTÁR GTFS-Realtime"

    def __init__(self, settings: Settings, client: httpx.Client | None = None):
        assert settings.bkk_api_key is not None
        self._key = settings.bkk_api_key.get_secret_value()
        self._base_url = settings.bkk_realtime_base_url.rstrip("/")
        self._client = client or httpx.Client(
            timeout=settings.http_timeout_seconds, headers={"User-Agent": settings.user_agent}
        )
        self._cache = TTLCache(settings.realtime_cache_ttl_seconds)

    @property
    def enabled(self) -> bool:
        return True

    @property
    def status_message(self) -> str:
        return "Live data from BKK FUTÁR (GTFS-Realtime), refreshed every few seconds."

    def close(self) -> None:
        self._client.close()

    def _fetch(self, feed_name: str) -> bytes:
        try:
            response = self._client.get(f"{self._base_url}/{feed_name}", params={"key": self._key})
            response.raise_for_status()
            return response.content
        except httpx.HTTPError as exc:
            # Never log the URL: it contains the API key.
            status = getattr(getattr(exc, "response", None), "status_code", "n/a")
            logger.warning("BKK real-time request for %s failed (HTTP %s)", feed_name, status)
            raise UpstreamServiceError("BKK real-time service is unavailable") from exc

    def _snapshot(self, feed_name: str, parser) -> RealtimeSnapshot:
        def load() -> RealtimeSnapshot:
            try:
                items, feed_time = parser(self._fetch(feed_name))
            except DecodeError as exc:
                raise UpstreamServiceError("BKK real-time feed could not be decoded") from exc
            return RealtimeSnapshot(
                items=items, feed_timestamp=feed_time, fetched_at=datetime.now(UTC)
            )

        return self._cache.get_or_set(feed_name, load)

    def vehicle_positions(self) -> RealtimeSnapshot[VehiclePosition]:
        return self._snapshot("VehiclePositions.pb", parse_vehicle_positions)

    def alerts(self) -> RealtimeSnapshot[ServiceAlert]:
        return self._snapshot("Alerts.pb", parse_alerts)
