"""Integration tests: import the mini GTFS feed into PostgreSQL and inspect the result."""

import shutil

from tests.conftest import MINI_GTFS, import_mini_feed


def count(db, sql: str, *params) -> int:
    return db.execute(sql, params).fetchone()["n"]


def test_row_counts(import_report):
    counts = import_report.row_counts
    assert counts["agencies"] == 2
    assert counts["routes"] == 4  # route with invalid route_type dropped
    assert counts["stops"] == 8  # entrance skipped, stop without coordinates dropped
    assert counts["shapes"] == 2  # single-point shape cannot form a line
    assert counts["trips"] == 7  # trip with unknown route dropped
    assert counts["stop_times"] == 17  # 2 orphans + 1 invalid time dropped
    assert counts["calendar"] == 0  # BKK-style feed: no calendar.txt
    assert counts["calendar_dates"] == 4
    assert counts["service_dates"] == 4


def test_invalid_rows_are_reported(import_report):
    text = "\n".join(import_report.warnings)
    assert "invalid route_type" in text
    assert "missing or invalid coordinates" in text
    assert "unknown route_id" in text
    assert "unknown trip_id/stop_id" in text
    assert "invalid time or sequence" in text
    assert "parent_station" in text


def test_ids_keep_leading_zeros(db):
    assert count(db, "SELECT count(*) AS n FROM stops WHERE stop_id = '001001'") == 1


def test_stop_geometry_and_parent(db):
    row = db.execute(
        "SELECT ST_X(geom) AS lon, ST_Y(geom) AS lat, parent_station FROM stops"
        " WHERE stop_id = '001001'"
    ).fetchone()
    assert (round(row["lon"], 4), round(row["lat"], 4)) == (19.0546, 47.4981)
    assert row["parent_station"] == "CS001"
    # unknown parent reference is cleared rather than failing the import
    assert (
        db.execute("SELECT parent_station FROM stops WHERE stop_id = '004001'").fetchone()[
            "parent_station"
        ]
        is None
    )


def test_route_modes_and_colors(db):
    rows = {r["route_id"]: r for r in db.execute("SELECT route_id, mode, color FROM routes")}
    assert rows["M2"]["mode"] == "metro"
    assert rows["TR70"]["mode"] == "trolleybus"
    assert rows["H5"]["mode"] == "hev"
    assert rows["B9"]["color"] == "009EE3"  # normalised to upper case


def test_times_after_midnight_are_stored_as_seconds(db):
    secs = db.execute(
        "SELECT departure_secs FROM stop_times WHERE trip_id = 'M2_NIGHT' AND stop_sequence = 1"
    ).fetchone()["departure_secs"]
    assert secs == 24 * 3600 + 30 * 60


def test_shapes_are_built_in_sequence_order(db):
    wkt = db.execute(
        "SELECT ST_AsText(geom) AS wkt FROM shapes WHERE shape_id = 'SH_M2_0'"
    ).fetchone()["wkt"]
    assert wkt == "LINESTRING(19.0546 47.4981,19.0605 47.4935,19.0703 47.4965)"


def test_missing_shape_reference_is_nulled(db):
    assert (
        db.execute("SELECT shape_id FROM trips WHERE trip_id = 'H5_T1'").fetchone()["shape_id"]
        is None
    )


def test_derived_stop_modes(db):
    modes = {r["stop_id"]: r["modes"] for r in db.execute("SELECT stop_id, modes FROM stops")}
    assert modes["001001"] == ["metro"]
    assert modes["002001"] == ["bus"]
    assert modes["004001"] == ["hev"]
    assert modes["CS001"] == ["metro"]  # station inherits from its platform
    assert modes["003001"] == []  # no service -> hidden from the map


def test_route_geometry_has_one_line_per_direction(db):
    row = db.execute(
        "SELECT ST_NumGeometries(geom) AS n FROM routes WHERE route_id = 'M2'"
    ).fetchone()
    assert row["n"] == 2


def test_feed_info_recorded(db):
    row = db.execute("SELECT * FROM feed_info ORDER BY imported_at DESC LIMIT 1").fetchone()
    assert row["feed_version"] == "test-1"
    assert str(row["feed_start_date"]) == "2026-10-04"


def test_reimport_replaces_data_instead_of_duplicating(database_url, db, tmp_path):
    import_mini_feed(database_url, tmp_path)
    assert count(db, "SELECT count(*) AS n FROM trips") == 7


def test_calendar_txt_rules_and_removals(database_url, db, tmp_path):
    """Weekly calendar.txt patterns are expanded; exception_type 2 removes a date."""
    feed = tmp_path / "feed"
    shutil.copytree(MINI_GTFS, feed)
    (feed / "calendar.txt").write_text(
        "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\n"
        "WK,1,1,1,1,1,0,0,20261005,20261011\n",
        encoding="utf-8",
    )
    with (feed / "calendar_dates.txt").open("a", encoding="utf-8") as file:
        file.write("WK,20261007,2\n")
    try:
        import_mini_feed(database_url, tmp_path / "dl", feed_dir=feed)
        dates = [
            str(r["service_date"])
            for r in db.execute(
                "SELECT service_date FROM service_dates WHERE service_id = 'WK' ORDER BY 1"
            )
        ]
        assert dates == ["2026-10-05", "2026-10-06", "2026-10-08", "2026-10-09"]
    finally:
        import_mini_feed(database_url, tmp_path / "restore")  # restore the shared fixture state
