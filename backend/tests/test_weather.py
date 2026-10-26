"""Weather/air-quality tests. Open-Meteo is mocked with respx: tests never hit the network."""

import httpx
import pytest
import respx

from app.services.weather import compass_direction, describe_weather_code, eaqi_label

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
AIR_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

FORECAST = {
    "latitude": 47.5,
    "longitude": 19.04,
    "current": {
        "time": "2026-10-05T08:00",
        "temperature_2m": 14.3,
        "apparent_temperature": 12.9,
        "relative_humidity_2m": 71,
        "precipitation": 0.4,
        "weather_code": 61,
        "is_day": 1,
        "wind_speed_10m": 12.2,
        "wind_direction_10m": 225,
        "wind_gusts_10m": 30.1,
    },
    "hourly": {
        "time": ["2026-10-05T08:00", "2026-10-05T09:00"],
        "temperature_2m": [14.3, 15.0],
        "precipitation_probability": [60, 40],
        "precipitation": [0.4, 0.1],
        "weather_code": [61, 3],
        "is_day": [1, 0],
    },
}

AIR = {
    "latitude": 47.5,
    "longitude": 19.0,
    "current": {
        "time": "2026-10-05T08:00",
        "european_aqi": 37,
        "pm10": 13.9,
        "pm2_5": 9.5,
        "nitrogen_dioxide": 22.7,
        "ozone": 75.0,
    },
}


@pytest.fixture(autouse=True)
def fresh_cache(client):
    client.app.state.weather.cache.clear()


@respx.mock
def test_weather_for_budapest(client):
    route = respx.get(FORECAST_URL).mock(return_value=httpx.Response(200, json=FORECAST))
    body = client.get("/api/weather").json()
    assert body["location"]["name"] == "Budapest"
    assert body["data_status"] == "model"
    current = body["current"]
    assert current["temperature_c"] == 14.3
    assert current["condition"] == "Slight rain"
    assert current["icon"] == "rain"
    assert current["wind_direction"] == "SW"
    assert current["precipitation_mm"] == 0.4
    assert len(body["hourly"]) == 2
    assert [h["is_day"] for h in body["hourly"]] == [True, False]
    assert "Open-Meteo" in body["attribution"]
    assert route.calls.last.request.url.params["timezone"] == "Europe/Budapest"


@respx.mock
def test_weather_is_cached(client):
    route = respx.get(FORECAST_URL).mock(return_value=httpx.Response(200, json=FORECAST))
    client.get("/api/weather")
    client.get("/api/weather")
    assert route.call_count == 1


@respx.mock
def test_weather_upstream_failure_returns_503(client):
    respx.get(FORECAST_URL).mock(return_value=httpx.Response(500))
    response = client.get("/api/weather")
    assert response.status_code == 503
    assert "Open-Meteo" in response.json()["detail"]


@respx.mock
def test_weather_unexpected_payload_returns_503(client):
    respx.get(FORECAST_URL).mock(return_value=httpx.Response(200, json={"oops": True}))
    assert client.get("/api/weather").status_code == 503


@respx.mock
def test_weather_timeout_returns_503(client):
    respx.get(FORECAST_URL).mock(side_effect=httpx.ConnectTimeout("timeout"))
    assert client.get("/api/weather").status_code == 503


def test_weather_location_validation(client):
    assert client.get("/api/weather?lat=40&lon=10").status_code == 422  # outside Budapest
    assert client.get("/api/weather?lat=47.5").status_code == 422  # lon missing
    assert client.get("/api/weather?lat=abc&lon=19").status_code == 422


@respx.mock
def test_custom_location_inside_budapest(client):
    respx.get(FORECAST_URL).mock(return_value=httpx.Response(200, json=FORECAST))
    body = client.get("/api/weather?lat=47.53&lon=19.05").json()
    assert body["location"]["name"] == "Selected location"


@respx.mock
def test_air_quality(client):
    respx.get(AIR_URL).mock(return_value=httpx.Response(200, json=AIR))
    body = client.get("/api/air-quality").json()
    assert body["current"]["european_aqi"] == 37
    assert body["current"]["european_aqi_label"] == "Fair"
    assert body["data_status"] == "model"


def test_helpers():
    assert describe_weather_code(0) == ("Clear sky", "clear")
    assert describe_weather_code(12345) == ("Unknown", "unknown")
    assert compass_direction(0) == "N" and compass_direction(359) == "N"
    assert compass_direction(90) == "E"
    assert eaqi_label(10) == "Good" and eaqi_label(150) == "Extremely poor"
    assert eaqi_label(None) is None
