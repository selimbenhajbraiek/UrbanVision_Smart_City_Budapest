from app.errors import FeatureNotConfiguredError

from .base import RealtimeProvider, RealtimeSnapshot, ServiceAlert, VehiclePosition

MESSAGE = (
    "Real-time data is not configured. Set BKK_API_KEY (free key from opendata.bkk.hu) "
    "to enable live vehicle positions and alerts. All departures shown are scheduled."
)


class DisabledRealtimeProvider(RealtimeProvider):
    name = None

    @property
    def enabled(self) -> bool:
        return False

    @property
    def status_message(self) -> str:
        return MESSAGE

    def vehicle_positions(self) -> RealtimeSnapshot[VehiclePosition]:
        raise FeatureNotConfiguredError(MESSAGE)

    def alerts(self) -> RealtimeSnapshot[ServiceAlert]:
        raise FeatureNotConfiguredError(MESSAGE)
