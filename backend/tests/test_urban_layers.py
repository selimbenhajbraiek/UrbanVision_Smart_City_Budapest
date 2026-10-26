"""Phase 8: OpenStreetMap urban layers (Overpass parsing, storage, API)."""

import httpx
import psycopg
import pytest
import respx

from app.urban_layers import URBAN_LAYERS
from ingestion.osm import OverpassError, build_query, fetch_layer, parse_overpass, store_layer

OVERPASS_URL = "https://overpass.example/api/interpreter"

OVERPASS_RESPONSE = {
    "osm3s": {"timestamp_osm_base": "2026-09-27T17:57:21Z"},
    "elements": [
        {
            "type": "node",
            "id": 1,
            "lat": 47.5,
            "lon": 19.05,
            "tags": {
                "amenity": "charging_station",
                "name": "Charger A",
                "operator": "ELMŰ",
                "capacity": "2",
                "socket:type2": "2",
                "internal_note": "not shown",
            },
        },
        {
            "type": "way",
            "id": 2,
            "center": {"lat": 47.51, "lon": 19.06},
            "tags": {"amenity": "charging_station"},
        },
        {"type": "relation", "id": 3, "tags": {}},  # no location -> skipped
    ],
}


def test_build_query_targets_budapest_area():
    query = build_query(URBAN_LAYERS["ev_charging"])
    assert "area(id:3600037244)" in query
    assert "out center tags" in query


def test_parse_overpass_uses_center_for_ways_and_skips_unlocated():
    pois, timestamp = parse_overpass(OVERPASS_RESPONSE)
    assert [(p.osm_type, p.osm_id) for p in pois] == [("node", 1), ("way", 2)]
    assert pois[1].lat == 47.51
    assert pois[0].name == "Charger A" and pois[0].operator == "ELMŰ"
    assert timestamp == "2026-09-27T17:57:21Z"


def test_parse_overpass_rejects_garbage():
    with pytest.raises(OverpassError):
        parse_overpass({"error": "bad"})


@respx.mock
def test_fetch_layer_retries_when_busy(monkeypatch):
    monkeypatch.setattr("ingestion.osm.time.sleep", lambda _: None)
    route = respx.post(OVERPASS_URL).mock(
        side_effect=[httpx.Response(429), httpx.Response(200, json=OVERPASS_RESPONSE)]
    )
    pois, _ = fetch_layer(URBAN_LAYERS["ev_charging"], OVERPASS_URL, "tests")
    assert len(pois) == 2
    assert route.call_count == 2


@respx.mock
def test_fetch_layer_gives_up_after_retries(monkeypatch):
    monkeypatch.setattr("ingestion.osm.time.sleep", lambda _: None)
    respx.post(OVERPASS_URL).mock(return_value=httpx.Response(504))
    with pytest.raises(OverpassError):
        fetch_layer(URBAN_LAYERS["ev_charging"], OVERPASS_URL, "tests", attempts=2)


@pytest.fixture
def stored_layer(database_url, import_report):
    pois, timestamp = parse_overpass(OVERPASS_RESPONSE)
    with psycopg.connect(database_url, autocommit=True) as conn:
        store_layer(conn, "ev_charging", pois, timestamp)
        yield
        conn.execute("DELETE FROM urban_pois; DELETE FROM urban_layer_imports")


def test_layers_listing(client, stored_layer):
    layers = {layer["id"]: layer for layer in client.get("/api/layers").json()}
    assert layers.keys() == URBAN_LAYERS.keys()
    assert layers["ev_charging"]["feature_count"] == 2
    assert layers["ev_charging"]["data_status"] == "static"
    assert layers["bike_rental"]["feature_count"] == 0


def test_layer_geojson_shows_only_popup_tags(client, stored_layer):
    body = client.get("/api/layers/ev_charging").json()
    assert len(body["features"]) == 2
    props = next(f for f in body["features"] if f["id"] == "node/1")["properties"]
    assert props["osm_url"] == "https://www.openstreetmap.org/node/1"
    assert props["details"] == {"operator": "ELMŰ", "capacity": "2", "socket:type2": "2"}


def test_layer_bbox_filter(client, stored_layer):
    body = client.get("/api/layers/ev_charging?bbox=19.04,47.49,19.055,47.505").json()
    assert [f["id"] for f in body["features"]] == ["node/1"]


def test_storing_again_replaces_features(database_url, client, stored_layer):
    pois, timestamp = parse_overpass(OVERPASS_RESPONSE)
    with psycopg.connect(database_url, autocommit=True) as conn:
        store_layer(conn, "ev_charging", pois[:1], timestamp)
    assert len(client.get("/api/layers/ev_charging").json()["features"]) == 1


def test_unknown_layer_404(client):
    assert client.get("/api/layers/unicorns").status_code == 404
