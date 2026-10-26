"""GTFS structure checks and value parsers.

Structural problems (missing files/columns) abort the import. Bad individual rows are
dropped or cleaned, and every such decision is recorded in the ImportReport.
"""

import csv
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd


class GtfsValidationError(Exception):
    """The feed is structurally invalid and cannot be imported."""


@dataclass(frozen=True)
class FileSpec:
    required: bool
    required_columns: tuple[str, ...]
    optional_columns: tuple[str, ...] = ()

    @property
    def columns(self) -> tuple[str, ...]:
        return self.required_columns + self.optional_columns


# Only the columns UrbanVision actually uses are read; everything else is ignored.
GTFS_FILES: dict[str, FileSpec] = {
    "agency.txt": FileSpec(
        True, ("agency_name",), ("agency_id", "agency_url", "agency_timezone", "agency_phone")
    ),
    "stops.txt": FileSpec(
        True,
        ("stop_id", "stop_name", "stop_lat", "stop_lon"),
        ("stop_code", "location_type", "parent_station", "wheelchair_boarding"),
    ),
    "routes.txt": FileSpec(
        True,
        ("route_id", "route_type"),
        (
            "agency_id",
            "route_short_name",
            "route_long_name",
            "route_desc",
            "route_color",
            "route_text_color",
            "route_sort_order",
        ),
    ),
    "trips.txt": FileSpec(
        True,
        ("route_id", "service_id", "trip_id"),
        ("trip_headsign", "direction_id", "shape_id", "wheelchair_accessible", "bikes_allowed"),
    ),
    "stop_times.txt": FileSpec(
        True,
        ("trip_id", "stop_id", "stop_sequence", "arrival_time", "departure_time"),
        ("stop_headsign", "pickup_type", "drop_off_type"),
    ),
    "calendar.txt": FileSpec(
        False,
        (
            "service_id",
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
            "start_date",
            "end_date",
        ),
    ),
    "calendar_dates.txt": FileSpec(False, ("service_id", "date", "exception_type")),
    "shapes.txt": FileSpec(
        False, ("shape_id", "shape_pt_lat", "shape_pt_lon", "shape_pt_sequence")
    ),
    "feed_info.txt": FileSpec(
        False, ("feed_publisher_name",), ("feed_version", "feed_start_date", "feed_end_date")
    ),
}


@dataclass
class ImportReport:
    source: str = ""
    row_counts: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    skipped: bool = False

    def warn(self, message: str) -> None:
        self.warnings.append(message)


class GtfsFeed:
    """Read access to an extracted GTFS directory."""

    def __init__(self, directory: Path):
        self.directory = directory

    def has(self, name: str) -> bool:
        return (self.directory / name).is_file()

    def header(self, name: str) -> list[str]:
        with (self.directory / name).open(encoding="utf-8-sig", newline="") as file:
            return [column.strip() for column in next(csv.reader(file), [])]

    def _read_kwargs(self, name: str) -> dict:
        present = set(self.header(name))
        return {
            # Everything is read as text: IDs such as "002133" must keep their leading zeros.
            "dtype": str,
            "keep_default_na": False,
            "na_values": [],
            "encoding": "utf-8-sig",
            "usecols": [c for c in GTFS_FILES[name].columns if c in present],
        }

    def read(self, name: str) -> pd.DataFrame:
        frame = pd.read_csv(self.directory / name, **self._read_kwargs(name))
        return _with_all_columns(frame, name).apply(lambda column: column.str.strip())

    def read_chunks(self, name: str, chunksize: int) -> Iterator[pd.DataFrame]:
        with pd.read_csv(
            self.directory / name, chunksize=chunksize, **self._read_kwargs(name)
        ) as reader:
            for chunk in reader:
                yield _with_all_columns(chunk, name)


def _with_all_columns(frame: pd.DataFrame, name: str) -> pd.DataFrame:
    """Add missing optional columns as empty strings so later code can rely on them."""
    for column in GTFS_FILES[name].columns:
        if column not in frame.columns:
            frame[column] = ""
    return frame


def check_structure(feed: GtfsFeed) -> None:
    """Raise GtfsValidationError if required files or columns are missing."""
    problems: list[str] = []
    for name, spec in GTFS_FILES.items():
        if not feed.has(name):
            if spec.required:
                problems.append(f"missing required file {name}")
            continue
        missing = [c for c in spec.required_columns if c not in feed.header(name)]
        if missing:
            problems.append(f"{name} is missing column(s): {', '.join(missing)}")
    if not feed.has("calendar.txt") and not feed.has("calendar_dates.txt"):
        problems.append("either calendar.txt or calendar_dates.txt is required")
    if problems:
        raise GtfsValidationError("Invalid GTFS feed: " + "; ".join(problems))


# ---------------------------------------------------------------------------
# Value parsers (vectorised with pandas; invalid values become <NA>)
# ---------------------------------------------------------------------------
def parse_int(series: pd.Series) -> pd.Series:
    numbers = pd.to_numeric(series.replace("", None), errors="coerce")
    return numbers.where(numbers == numbers.round()).astype("Int64")


def parse_float(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.replace("", None), errors="coerce").astype("Float64")


def parse_gtfs_time(series: pd.Series) -> pd.Series:
    """'25:10:00' -> 90600 seconds since service-day start. Invalid/empty -> <NA>."""
    parts = series.str.extract(r"^(\d{1,3}):([0-5]\d):([0-5]\d)$")
    hours, minutes, seconds = (pd.to_numeric(parts[i]) for i in range(3))
    return (hours * 3600 + minutes * 60 + seconds).astype("Int64")


def parse_gtfs_date(series: pd.Series) -> pd.Series:
    """'20260926' -> '2026-09-26' (ISO text for PostgreSQL). Invalid -> <NA>."""
    dates = pd.to_datetime(series, format="%Y%m%d", errors="coerce")
    return dates.dt.strftime("%Y-%m-%d").astype("string")


def parse_color(series: pd.Series) -> pd.Series:
    """Keep valid 6-digit hex colours (upper-case), otherwise <NA>."""
    upper = series.str.upper().str.lstrip("#")
    return upper.where(upper.str.fullmatch(r"[0-9A-F]{6}"), None).astype("string")


def blank_to_na(series: pd.Series) -> pd.Series:
    return series.replace("", None).astype("string")
