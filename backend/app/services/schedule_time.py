"""Converting GTFS schedule times to real clock times.

GTFS times are measured from "noon minus 12 hours" on the service date, in local time.
That is normally midnight, but on daylight-saving change days it is 23:00 or 01:00.
Times may exceed 24:00:00 (e.g. 25:10:00 = 01:10 the next morning for a trip that
belongs to the previous day's service).
"""

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo


def service_day_start(service_date: date, tz: ZoneInfo) -> datetime:
    noon = datetime.combine(service_date, time(12), tzinfo=tz)
    return noon.astimezone(UTC) - timedelta(hours=12)


def schedule_to_datetime(service_date: date, seconds: int, tz: ZoneInfo) -> datetime:
    return (service_day_start(service_date, tz) + timedelta(seconds=seconds)).astimezone(tz)


def seconds_since_service_start(moment: datetime, service_date: date, tz: ZoneInfo) -> int:
    return int((moment - service_day_start(service_date, tz)).total_seconds())


def format_gtfs_seconds(seconds: int) -> str:
    return f"{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"
