"""Real-time transit data (Phase 10).

The API only talks to the abstract `RealtimeProvider`. Without a BKK API key the
`DisabledRealtimeProvider` is used, and the UI clearly shows that live data is off —
UrbanVision never invents vehicle positions.
"""

from app.config import Settings

from .base import RealtimeProvider
from .bkk_gtfs_rt import BkkGtfsRealtimeProvider
from .disabled import DisabledRealtimeProvider


def create_realtime_provider(settings: Settings) -> RealtimeProvider:
    if settings.realtime_enabled:
        return BkkGtfsRealtimeProvider(settings)
    return DisabledRealtimeProvider()


__all__ = ["RealtimeProvider", "create_realtime_provider"]
