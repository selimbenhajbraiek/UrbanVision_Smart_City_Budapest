"""API tests for stops, departures and search (mini GTFS feed)."""


def feature_ids(geojson: dict) -> set[str]:
    return {f["properties"]["stop_id"] for f in geojson["features"]}


def test_list_stops_returns_geojson_of_served_stops(client):
    response = client.get("/api/stops")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/geo+json")
    body = response.json()
    assert body["type"] == "FeatureCollection"
    # stations, unused stops and dropped stops are not mapped
    assert feature_ids(body) == {"001001", "001002", "001003", "002001", "002002", "004001"}
    feature = next(f for f in body["features"] if f["id"] == "001001")
    assert feature["geometry"] == {"type": "Point", "coordinates": [19.0546, 47.4981]}
    assert feature["properties"]["modes"] == ["metro"]


def test_list_stops_filters_by_bbox_and_mode(client):
    bbox = "19.050,47.495,19.058,47.500"  # around Deák Ferenc tér
    assert feature_ids(client.get(f"/api/stops?bbox={bbox}").json()) == {"001001", "002001"}
    assert feature_ids(client.get(f"/api/stops?bbox={bbox}&mode=bus").json()) == {"002001"}
    assert feature_ids(client.get("/api/stops?mode=hev").json()) == {"004001"}


def test_list_stops_limit(client):
    assert len(client.get("/api/stops?limit=2").json()["features"]) == 2


def test_invalid_stop_queries_return_422(client):
    assert client.get("/api/stops?bbox=1,2,3").status_code == 422
    assert client.get("/api/stops?bbox=20,48,19,47").status_code == 422  # min > max
    assert client.get("/api/stops?mode=spaceship").status_code == 422
    assert client.get("/api/stops?limit=0").status_code == 422


def test_stop_detail(client):
    body = client.get("/api/stops/001001").json()
    assert body["name"] == "Deák Ferenc tér"
    assert body["parent_station"] == "CS001"
    assert [r["short_name"] for r in body["routes"]] == ["M2"]
    # "Deák Ferenc tér M" bus stop is recognised as part of the same interchange
    assert [s["stop_id"] for s in body["nearby_platforms"]] == ["002001"]


def test_station_detail_lists_routes_of_its_platforms(client):
    body = client.get("/api/stops/CS001").json()
    assert [r["route_id"] for r in body["routes"]] == ["M2"]


def test_unknown_stop_returns_404(client):
    assert client.get("/api/stops/NOPE").status_code == 404
    assert client.get("/api/stops/NOPE/departures").status_code == 404


def departures(client, stop_id: str, **params) -> dict:
    response = client.get(f"/api/stops/{stop_id}/departures", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def test_scheduled_departures_are_sorted_and_labelled(client):
    body = departures(client, "001001", date="2026-10-05", time="07:55", minutes=120)
    assert body["data_status"] == "scheduled"
    assert body["schedule_available"] is True
    assert [(d["trip_id"], d["minutes_until"]) for d in body["departures"]] == [
        ("M2_T1", 5),
        ("M2_T2", 15),
    ]
    first = body["departures"][0]
    assert first["departure_time"] == "2026-10-05T08:00:00+02:00"
    assert first["headsign"] == "Örs vezér tere"
    assert first["color"] == "E41F18"


def test_arrivals_at_terminus_are_not_departures(client):
    body = departures(client, "001001", date="2026-10-05", time="08:08", minutes=5)
    assert all(d["trip_id"] != "M2_T3" for d in body["departures"])


def test_station_departures_include_its_platforms(client):
    body = departures(client, "CS001", date="2026-10-05", time="07:55", minutes=30)
    assert [d["trip_id"] for d in body["departures"]] == ["M2_T1", "M2_T2"]


def test_late_night_trip_of_previous_service_day(client):
    body = departures(client, "001001", date="2026-10-05", time="00:15", minutes=60)
    [night] = body["departures"]
    assert night["trip_id"] == "M2_NIGHT"
    assert night["service_date"] == "2026-10-04"
    assert night["scheduled_time"] == "24:30:00"
    assert night["departure_time"] == "2026-10-05T00:30:00+02:00"


def test_window_crossing_midnight_includes_next_service_day(client):
    body = departures(client, "001001", date="2026-10-05", time="23:50", minutes=600)
    assert [(d["trip_id"], d["service_date"]) for d in body["departures"]] == [
        ("M2_NIGHT", "2026-10-05"),
        ("M2_T1", "2026-10-06"),
        ("M2_T2", "2026-10-06"),
    ]


def test_service_calendar_is_respected(client):
    # B9_SUN only runs on 2026-10-04; B9_T1 uses the stop headsign override
    sunday = departures(client, "002001", date="2026-10-04", time="08:00")
    assert [d["trip_id"] for d in sunday["departures"]] == ["B9_T1", "B9_SUN"]
    assert sunday["departures"][0]["headsign"] == "Kálvin tér (via Astoria)"
    monday = departures(client, "002001", date="2026-10-05", time="08:00")
    assert [d["trip_id"] for d in monday["departures"]] == ["B9_T1"]


def test_date_outside_feed_is_reported(client):
    body = departures(client, "001001", date="2027-01-01", time="08:00")
    assert body["schedule_available"] is False
    assert body["departures"] == []
    assert "does not cover" in body["notice"]


def test_invalid_departure_parameters(client):
    assert client.get("/api/stops/001001/departures?time=25:00").status_code == 422
    assert client.get("/api/stops/001001/departures?date=2026-13-01").status_code == 422
    assert client.get("/api/stops/001001/departures?minutes=0").status_code == 422
    assert client.get("/api/stops/001001/departures?limit=1000").status_code == 422


def test_search_is_accent_insensitive_and_groups_platforms(client):
    body = client.get("/api/search?q=deak").json()
    names = [s["name"] for s in body["stops"]]
    assert "Deák Ferenc tér" in names and "Deák Ferenc tér M" in names


def test_search_finds_routes_by_number(client):
    body = client.get("/api/search?q=m2").json()
    assert body["routes"][0]["route_id"] == "M2"


def test_search_requires_two_characters(client):
    assert client.get("/api/search?q=a").status_code == 422
