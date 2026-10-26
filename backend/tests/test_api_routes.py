"""API tests for routes, meta, stats and health (mini GTFS feed)."""


def test_list_routes_sorted_by_official_order(client):
    body = client.get("/api/routes").json()
    assert [r["route_id"] for r in body] == ["M2", "H5", "B9", "TR70"]


def test_list_routes_filter_by_mode(client):
    assert [r["route_id"] for r in client.get("/api/routes?mode=bus,trolleybus").json()] == [
        "B9",
        "TR70",
    ]


def test_list_routes_text_search(client):
    assert [r["route_id"] for r in client.get("/api/routes?q=szentendre").json()] == ["H5"]


def test_route_detail(client):
    body = client.get("/api/routes/M2").json()
    assert body["short_name"] == "M2"
    assert body["agency_name"] == "BKK"
    assert body["geometry"]["type"] == "MultiLineString"
    directions = {d["direction_id"]: d for d in body["directions"]}
    assert directions[0]["headsign"] == "Örs vezér tere"
    assert [s["stop_id"] for s in directions[0]["stops"]] == ["001001", "001002", "001003"]
    assert [s["stop_id"] for s in directions[1]["stops"]] == ["001003", "001002", "001001"]


def test_route_without_shape_has_no_geometry(client):
    assert client.get("/api/routes/B9").json()["geometry"] is None


def test_unknown_route_returns_404(client):
    response = client.get("/api/routes/NOPE")
    assert response.status_code == 404
    assert response.json() == {"detail": "Route 'NOPE' not found"}


def test_route_geometry_collection(client):
    body = client.get("/api/routes/geometry").json()
    assert [f["id"] for f in body["features"]] == ["M2"]  # only routes with shapes
    assert body["features"][0]["properties"]["color"] == "E41F18"
    assert client.get("/api/routes/geometry?mode=bus").json()["features"] == []
    assert client.get("/api/routes/geometry?route_id=M2,B9").json()["features"][0]["id"] == "M2"


def test_route_geometry_invalid_mode(client):
    assert client.get("/api/routes/geometry?mode=rocket").status_code == 422


def test_health(client):
    assert client.get("/api/health").json() == {
        "status": "ok",
        "database": "ok",
        "gtfs_loaded": True,
    }


def test_meta_contains_feed_and_attributions(client):
    body = client.get("/api/meta").json()
    assert body["feed"]["feed_version"] == "test-1"
    assert body["feed"]["valid_from"] == "2026-10-04"
    assert body["realtime"]["enabled"] is False
    assert {s["id"] for s in body["data_sources"]} >= {"osm", "bkk_gtfs", "open_meteo"}


def test_stats(client):
    body = client.get("/api/stats").json()
    assert body["stops"] == 6
    assert body["stations"] == 1
    assert body["routes"] == 4
    assert body["transport_modes"] == 4
    assert body["routes_by_mode"] == {"metro": 1, "hev": 1, "bus": 1, "trolleybus": 1}
    assert body["stops_by_mode"]["metro"] == 3


def test_openapi_docs_available(client):
    assert client.get("/openapi.json").status_code == 200
