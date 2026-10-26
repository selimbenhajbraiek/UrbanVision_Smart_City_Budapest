"""Open-Meteo client for current weather and air quality (no API key required).

Responses are cached for WEATHER_CACHE_TTL_SECONDS so that many browser users cause only
one upstream request per location and time window (Open-Meteo fair-use policy).
"""

import logging
from datetime import UTC, datetime

import httpx
from pydantic import BaseModel, ValidationError

from app.config import BUDAPEST_CENTER, Settings
from app.errors import UpstreamServiceError
from app.schemas.weather import (
    AirQualityResponse,
    CurrentAirQuality,
    CurrentWeather,
    HourlyForecast,
    Location,
    WeatherResponse,
)
from app.services.cache import TTLCache

logger = logging.getLogger(__name__)

WEATHER_ATTRIBUTION = "Weather data by Open-Meteo.com (CC BY 4.0)"
AIR_QUALITY_ATTRIBUTION = (
    "Air quality by Open-Meteo.com (CC BY 4.0), based on Copernicus CAMS European forecasts"
)

# WMO weather interpretation codes -> (description, icon keyword used by the frontend)
WMO_CODES: dict[int, tuple[str, str]] = {
    0: ("Clear sky", "clear"),
    1: ("Mainly clear", "clear"),
    2: ("Partly cloudy", "partly-cloudy"),
    3: ("Overcast", "cloudy"),
    45: ("Fog", "fog"),
    48: ("Depositing rime fog", "fog"),
    51: ("Light drizzle", "drizzle"),
    53: ("Moderate drizzle", "drizzle"),
    55: ("Dense drizzle", "drizzle"),
    56: ("Light freezing drizzle", "drizzle"),
    57: ("Dense freezing drizzle", "drizzle"),
    61: ("Slight rain", "rain"),
    63: ("Moderate rain", "rain"),
    65: ("Heavy rain", "rain"),
    66: ("Light freezing rain", "rain"),
    67: ("Heavy freezing rain", "rain"),
    71: ("Slight snowfall", "snow"),
    73: ("Moderate snowfall", "snow"),
    75: ("Heavy snowfall", "snow"),
    77: ("Snow grains", "snow"),
    80: ("Slight rain showers", "rain"),
    81: ("Moderate rain showers", "rain"),
    82: ("Violent rain showers", "rain"),
    85: ("Slight snow showers", "snow"),
    86: ("Heavy snow showers", "snow"),
    95: ("Thunderstorm", "thunderstorm"),
    96: ("Thunderstorm with slight hail", "thunderstorm"),
    99: ("Thunderstorm with heavy hail", "thunderstorm"),
}

# European Air Quality Index bands (upper bound, label)
EAQI_BANDS = [(20, "Good"), (40, "Fair"), (60, "Moderate"), (80, "Poor"), (100, "Very poor")]

COMPASS_POINTS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]


def describe_weather_code(code: int) -> tuple[str, str]:
    return WMO_CODES.get(code, ("Unknown", "unknown"))


def compass_direction(degrees: float) -> str:
    return COMPASS_POINTS[round((degrees % 360) / 45) % 8]


def eaqi_label(value: float | None) -> str | None:
    if value is None:
        return None
    for upper_bound, label in EAQI_BANDS:
        if value <= upper_bound:
            return label
    return "Extremely poor"


# --- Shapes of the upstream JSON we rely on (validated, so API changes fail loudly) ---
class _OMCurrent(BaseModel):
    time: str
    temperature_2m: float
    apparent_temperature: float | None = None
    relative_humidity_2m: float | None = None
    precipitation: float | None = None
    weather_code: int
    is_day: int | None = None
    wind_speed_10m: float
    wind_direction_10m: float | None = None
    wind_gusts_10m: float | None = None


class _OMHourly(BaseModel):
    time: list[str]
    temperature_2m: list[float | None]
    precipitation_probability: list[float | None]
    precipitation: list[float | None]
    weather_code: list[int | None]
    is_day: list[int | None] | None = None


class _OMForecast(BaseModel):
    latitude: float
    longitude: float
    current: _OMCurrent
    hourly: _OMHourly


class _OMAirCurrent(BaseModel):
    time: str
    european_aqi: float | None = None
    pm10: float | None = None
    pm2_5: float | None = None
    nitrogen_dioxide: float | None = None
    ozone: float | None = None


class _OMAirQuality(BaseModel):
    latitude: float
    longitude: float
    current: _OMAirCurrent


class WeatherService:
    def __init__(self, settings: Settings, client: httpx.Client | None = None):
        self.settings = settings
        self.client = client or httpx.Client(
            timeout=settings.http_timeout_seconds, headers={"User-Agent": settings.user_agent}
        )
        self.cache = TTLCache(settings.weather_cache_ttl_seconds)

    def close(self) -> None:
        self.client.close()

    def _get_json(self, url: str, params: dict) -> dict:
        try:
            response = self.client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("Open-Meteo request failed: %s", exc)
            raise UpstreamServiceError("Weather service (Open-Meteo) is unavailable") from exc

    @staticmethod
    def _location(lat: float, lon: float) -> Location:
        is_center = (round(lat, 3), round(lon, 3)) == (
            round(BUDAPEST_CENTER[0], 3),
            round(BUDAPEST_CENTER[1], 3),
        )
        return Location(
            name="Budapest" if is_center else "Selected location", latitude=lat, longitude=lon
        )

    def get_weather(self, lat: float, lon: float) -> WeatherResponse:
        key = ("weather", round(lat, 2), round(lon, 2))
        return self.cache.get_or_set(key, lambda: self._fetch_weather(lat, lon))

    def _fetch_weather(self, lat: float, lon: float) -> WeatherResponse:
        raw = self._get_json(
            self.settings.open_meteo_forecast_url,
            {
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,apparent_temperature,relative_humidity_2m,"
                "precipitation,weather_code,is_day,wind_speed_10m,wind_direction_10m,"
                "wind_gusts_10m",
                "hourly": "temperature_2m,precipitation_probability,precipitation,"
                "weather_code,is_day",
                "forecast_hours": 12,
                "timezone": self.settings.timezone,
                "wind_speed_unit": "kmh",
            },
        )
        try:
            data = _OMForecast.model_validate(raw)
        except ValidationError as exc:
            logger.warning("Unexpected Open-Meteo forecast payload: %s", exc)
            raise UpstreamServiceError("Weather service returned unexpected data") from exc

        current = data.current
        condition, icon = describe_weather_code(current.weather_code)
        hourly = []
        h = data.hourly
        for i, time in enumerate(h.time):
            code = h.weather_code[i]
            hour_condition, hour_icon = (
                describe_weather_code(code) if code is not None else (None, None)
            )
            hourly.append(
                HourlyForecast(
                    time=time,
                    temperature_c=h.temperature_2m[i],
                    precipitation_probability_percent=h.precipitation_probability[i],
                    precipitation_mm=h.precipitation[i],
                    weather_code=code,
                    condition=hour_condition,
                    icon=hour_icon,
                    is_day=None if not h.is_day or h.is_day[i] is None else bool(h.is_day[i]),
                )
            )
        return WeatherResponse(
            location=self._location(lat, lon),
            current=CurrentWeather(
                time=current.time,
                temperature_c=current.temperature_2m,
                apparent_temperature_c=current.apparent_temperature,
                humidity_percent=current.relative_humidity_2m,
                precipitation_mm=current.precipitation,
                weather_code=current.weather_code,
                condition=condition,
                icon=icon,
                is_day=None if current.is_day is None else bool(current.is_day),
                wind_speed_kmh=current.wind_speed_10m,
                wind_direction_deg=current.wind_direction_10m,
                wind_direction=None
                if current.wind_direction_10m is None
                else compass_direction(current.wind_direction_10m),
                wind_gusts_kmh=current.wind_gusts_10m,
            ),
            hourly=hourly,
            fetched_at=datetime.now(UTC),
            attribution=WEATHER_ATTRIBUTION,
        )

    def get_air_quality(self, lat: float, lon: float) -> AirQualityResponse:
        key = ("air", round(lat, 2), round(lon, 2))
        return self.cache.get_or_set(key, lambda: self._fetch_air_quality(lat, lon))

    def _fetch_air_quality(self, lat: float, lon: float) -> AirQualityResponse:
        raw = self._get_json(
            self.settings.open_meteo_air_quality_url,
            {
                "latitude": lat,
                "longitude": lon,
                "current": "european_aqi,pm10,pm2_5,nitrogen_dioxide,ozone",
                "timezone": self.settings.timezone,
            },
        )
        try:
            data = _OMAirQuality.model_validate(raw)
        except ValidationError as exc:
            logger.warning("Unexpected Open-Meteo air-quality payload: %s", exc)
            raise UpstreamServiceError("Air-quality service returned unexpected data") from exc
        c = data.current
        return AirQualityResponse(
            location=self._location(lat, lon),
            current=CurrentAirQuality(
                time=c.time,
                european_aqi=c.european_aqi,
                european_aqi_label=eaqi_label(c.european_aqi),
                pm10_ugm3=c.pm10,
                pm2_5_ugm3=c.pm2_5,
                nitrogen_dioxide_ugm3=c.nitrogen_dioxide,
                ozone_ugm3=c.ozone,
            ),
            fetched_at=datetime.now(UTC),
            attribution=AIR_QUALITY_ATTRIBUTION,
        )
