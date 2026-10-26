"""Unit tests for GTFS parsing/validation helpers (no database needed)."""

import shutil
import zipfile

import pandas as pd
import pytest

from app.transport_modes import mode_for_route_type, parse_modes
from ingestion.gtfs.source import GtfsSourceError, extract_feed
from ingestion.gtfs.validate import (
    GtfsFeed,
    GtfsValidationError,
    check_structure,
    parse_color,
    parse_gtfs_date,
    parse_gtfs_time,
    parse_int,
)
from tests.conftest import MINI_GTFS


def test_parse_gtfs_time_handles_times_after_midnight_and_invalid_values():
    parsed = parse_gtfs_time(pd.Series(["08:00:00", "25:10:00", "7:05:09", "xx:yy:zz", ""]))
    assert parsed.tolist()[:3] == [28800, 90600, 25509]
    assert parsed.isna().tolist()[3:] == [True, True]


def test_parse_gtfs_date():
    parsed = parse_gtfs_date(pd.Series(["20261004", "notadate"]))
    assert parsed.iloc[0] == "2026-10-04"
    assert pd.isna(parsed.iloc[1])


def test_parse_int_rejects_non_integers():
    parsed = parse_int(pd.Series(["3", "", "abc", "1.5"]))
    assert parsed.iloc[0] == 3
    assert parsed.isna().tolist()[1:] == [True, True, True]


def test_parse_color_normalises_and_rejects_invalid():
    assert parse_color(pd.Series(["009ee3", "#FFD800", "red", ""])).tolist()[:2] == [
        "009EE3",
        "FFD800",
    ]
    assert parse_color(pd.Series(["red"])).isna().all()


@pytest.mark.parametrize(
    ("route_type", "mode"),
    [
        (0, "tram"),
        (1, "metro"),
        (3, "bus"),
        (4, "boat"),
        (11, "trolleybus"),
        (109, "hev"),
        (700, "bus"),
        (900, "tram"),
        (401, "metro"),
        (1200, "boat"),
        (9999, "other"),
    ],
)
def test_mode_for_route_type(route_type, mode):
    assert mode_for_route_type(route_type) == mode


def test_parse_modes_rejects_unknown_values():
    assert parse_modes("Metro, tram") == ["metro", "tram"]
    assert parse_modes("") is None
    with pytest.raises(ValueError, match="spaceship"):
        parse_modes("metro,spaceship")


def test_mini_feed_passes_structure_check():
    check_structure(GtfsFeed(MINI_GTFS))  # does not raise


def test_leading_zeros_are_preserved_when_reading():
    stops = GtfsFeed(MINI_GTFS).read("stops.txt")
    assert "001001" in stops["stop_id"].tolist()


def test_missing_required_file_is_rejected(tmp_path):
    shutil.copytree(MINI_GTFS, tmp_path / "feed")
    (tmp_path / "feed" / "stops.txt").unlink()
    with pytest.raises(GtfsValidationError, match="missing required file stops.txt"):
        check_structure(GtfsFeed(tmp_path / "feed"))


def test_missing_required_column_is_rejected(tmp_path):
    shutil.copytree(MINI_GTFS, tmp_path / "feed")
    (tmp_path / "feed" / "routes.txt").write_text(
        "route_id,route_short_name\nX,1\n", encoding="utf-8"
    )
    with pytest.raises(GtfsValidationError, match="routes.txt is missing column"):
        check_structure(GtfsFeed(tmp_path / "feed"))


def test_feed_without_any_calendar_is_rejected(tmp_path):
    shutil.copytree(MINI_GTFS, tmp_path / "feed")
    (tmp_path / "feed" / "calendar_dates.txt").unlink()
    with pytest.raises(GtfsValidationError, match="calendar"):
        check_structure(GtfsFeed(tmp_path / "feed"))


def test_extract_feed_flattens_nested_folders(tmp_path):
    archive = tmp_path / "feed.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        for file in MINI_GTFS.iterdir():
            zf.write(file, f"nested/{file.name}")
    out = extract_feed(archive, tmp_path / "out")
    assert (out / "stops.txt").is_file()


def test_extract_feed_rejects_non_zip(tmp_path):
    bogus = tmp_path / "feed.zip"
    bogus.write_text("not a zip")
    with pytest.raises(GtfsSourceError):
        extract_feed(bogus, tmp_path / "out")
