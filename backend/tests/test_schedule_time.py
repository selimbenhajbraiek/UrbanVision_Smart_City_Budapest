from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.services.departures import build_windows
from app.services.schedule_time import (
    format_gtfs_seconds,
    schedule_to_datetime,
    seconds_since_service_start,
)

BUDAPEST = ZoneInfo("Europe/Budapest")


def test_normal_day():
    assert schedule_to_datetime(date(2026, 10, 5), 8 * 3600, BUDAPEST) == datetime(
        2026, 10, 5, 8, 0, tzinfo=BUDAPEST
    )


def test_time_after_midnight_belongs_to_next_calendar_day():
    moment = schedule_to_datetime(date(2026, 10, 5), 25 * 3600 + 10 * 60, BUDAPEST)
    assert moment.isoformat() == "2026-10-06T01:10:00+02:00"


def test_daylight_saving_end_day_uses_noon_minus_twelve_hours():
    # 25 Oct 2026: clocks go back 03:00 CEST -> 02:00 CET. GTFS "12:00:00" must still be noon.
    assert schedule_to_datetime(date(2026, 10, 25), 12 * 3600, BUDAPEST).hour == 12


def test_round_trip():
    moment = datetime(2026, 10, 5, 7, 55, tzinfo=BUDAPEST)
    assert seconds_since_service_start(moment, date(2026, 10, 5), BUDAPEST) == 28500
    assert seconds_since_service_start(moment, date(2026, 10, 4), BUDAPEST) == 28500 + 86400


def test_build_windows_covers_three_service_days():
    windows = build_windows(datetime(2026, 10, 5, 0, 15, tzinfo=BUDAPEST), 60, BUDAPEST)
    assert [(str(w.service_date), w.from_secs, w.to_secs) for w in windows] == [
        ("2026-10-04", 87300, 90900),
        ("2026-10-05", 900, 4500),
        ("2026-10-06", -85500, -81900),
    ]


def test_format_gtfs_seconds():
    assert format_gtfs_seconds(90600) == "25:10:00"
