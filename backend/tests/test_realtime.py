"""Phase 10: real-time provider. BKK's endpoint is mocked with a synthetic protobuf feed."""

import time

import httpx
import pytest
import respx
from fastapi.testclient import TestClient
from google.transit import gtfs_realtime_pb2
from pydantic import SecretStr

from app.main import create_app

BASE = "https://rt.example/gtfs-rt/full"


def vehicle_feed() -> bytes:
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    feed.header.timestamp = int(time.time())
    status = gtfs_realtime_pb2.VehiclePosition.VehicleStopStatus
    for vehicle_id, trip_id, route_id in (
        ("V1", "M2_T1", "M2"),
        ("V2", "B9_T1", "B9"),
        ("V3", "", ""),  # idle: no trip assigned
        ("V4", "NEWER_FEED_TRIP", "M2"),  # trip unknown to the imported timetable
    ):
        entity = feed.entity.add(id=vehicle_id)
        entity.vehicle.vehicle.id = vehicle_id
        if trip_id:
            entity.vehicle.trip.trip_id = trip_id
            entity.vehicle.trip.route_id = route_id
        entity.vehicle.position.latitude = 47.5
        entity.vehicle.position.longitude = 19.05
        entity.vehicle.position.speed = 10.0  # m/s
    v1 = feed.entity[0].vehicle
    v1.stop_id = "001002"
    v1.current_status = status.Value("STOPPED_AT")
    v1.vehicle.license_plate = "AAA-123"
    v1.vehicle.wheelchair_accessible = gtfs_realtime_pb2.VehicleDescriptor.WHEELCHAIR_ACCESSIBLE
    feed.entity[3].vehicle.vehicle.label = "Örs vezér tere (BKK label)"
    feed.entity.add(id="no-position")  # ignored: no vehicle position
    return feed.SerializeToString()


def alerts_feed() -> bytes:
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    entity = feed.entity.add(id="A1")
    entity.alert.header_text.translation.add(text="Pótlóbusz", language="hu")
    entity.alert.header_text.translation.add(text="Replacement bus", language="en")
    entity.alert.informed_entity.add(route_id="M2")
    return feed.SerializeToString()


def test_realtime_disabled_by_default(client):
    assert client.get("/api/realtime/status").json()["enabled"] is False
    response = client.get("/api/realtime/vehicles")
    assert response.status_code == 503
    assert "BKK_API_KEY" in response.json()["detail"]
    assert client.get("/api/realtime/alerts").status_code == 503


@pytest.fixture
def realtime_client(settings, import_report):
    enabled = settings.model_copy(
        update={"bkk_api_key": SecretStr("test-key"), "bkk_realtime_base_url": BASE}
    )
    with TestClient(create_app(enabled)) as test_client:
        yield test_client


@respx.mock
def test_vehicles_are_decorated_with_route_info(realtime_client):
    route = respx.get(f"{BASE}/VehiclePositions.pb").mock(
        return_value=httpx.Response(200, content=vehicle_feed())
    )
    body = realtime_client.get("/api/realtime/vehicles").json()
    assert body["data_status"] == "realtime"
    # idle vehicles (no trip) are hidden by default
    assert [v["vehicle_id"] for v in body["vehicles"]] == ["V1", "V2", "V4"]
    v1 = body["vehicles"][0]
    assert (v1["route_short_name"], v1["mode"], v1["color"]) == ("M2", "metro", "E41F18")
    assert v1["speed_kmh"] == 36.0
    assert route.calls.last.request.url.params["key"] == "test-key"
    # mode filter
    body = realtime_client.get("/api/realtime/vehicles?mode=bus").json()
    assert [v["vehicle_id"] for v in body["vehicles"]] == ["V2"]


@respx.mock
def test_vehicle_explains_where_it_is_going(realtime_client):
    respx.get(f"{BASE}/VehiclePositions.pb").mock(
        return_value=httpx.Response(200, content=vehicle_feed())
    )
    vehicles = {
        v["vehicle_id"]: v for v in realtime_client.get("/api/realtime/vehicles").json()["vehicles"]
    }
    v1 = vehicles["V1"]
    assert v1["in_service"] and v1["trip_in_timetable"]
    assert v1["headsign"] == "Örs vezér tere"
    assert v1["final_stop"] == "Blaha Lujza tér"
    assert (v1["next_stop_id"], v1["next_stop_name"]) == ("001002", "Astoria")
    assert v1["current_status"] == "stopped_at"
    assert v1["license_plate"] == "AAA-123"
    assert v1["wheelchair_accessible"] is True
    assert v1["route_description"] == "Déli pályaudvar / Örs vezér tere"
    # unknown trip: line still known from route_id, headsign falls back to BKK's label
    v4 = vehicles["V4"]
    assert (v4["trip_in_timetable"], v4["route_short_name"]) == (False, "M2")
    assert v4["headsign"] == "Örs vezér tere (BKK label)"
    assert v4["final_stop"] is None


@respx.mock
def test_idle_vehicles_on_request(realtime_client):
    respx.get(f"{BASE}/VehiclePositions.pb").mock(
        return_value=httpx.Response(200, content=vehicle_feed())
    )
    body = realtime_client.get("/api/realtime/vehicles?include_idle=true").json()
    idle = next(v for v in body["vehicles"] if v["vehicle_id"] == "V3")
    assert idle["in_service"] is False and idle["route_id"] is None


@respx.mock
def test_alerts_prefer_english(realtime_client):
    respx.get(f"{BASE}/Alerts.pb").mock(return_value=httpx.Response(200, content=alerts_feed()))
    [alert] = realtime_client.get("/api/realtime/alerts").json()["alerts"]
    assert alert["header"] == "Replacement bus"
    assert alert["route_ids"] == ["M2"]


@respx.mock
def test_upstream_errors_become_503(realtime_client):
    respx.get(f"{BASE}/VehiclePositions.pb").mock(return_value=httpx.Response(401))
    assert realtime_client.get("/api/realtime/vehicles").status_code == 503


@respx.mock
def test_garbage_protobuf_becomes_503(realtime_client):
    respx.get(f"{BASE}/Alerts.pb").mock(return_value=httpx.Response(200, content=b"\xff\xff"))
    assert realtime_client.get("/api/realtime/alerts").status_code == 503
