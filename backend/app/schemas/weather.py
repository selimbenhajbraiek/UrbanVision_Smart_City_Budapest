from datetime import datetime

from pydantic import BaseModel

from app.schemas import DataStatus


class Location(BaseModel):
    name: str
    latitude: float
    longitude: float


class CurrentWeather(BaseModel):
    time: str  # local time (Europe/Budapest) of the model step, e.g. "2026-09-27T19:30"
    temperature_c: float
    apparent_temperature_c: float | None
    humidity_percent: float | None
    precipitation_mm: float | None
    weather_code: int
    condition: str
    icon: str
    is_day: bool | None
    wind_speed_kmh: float
    wind_direction_deg: float | None
    wind_direction: str | None
    wind_gusts_kmh: float | None


class HourlyForecast(BaseModel):
    time: str
    temperature_c: float | None
    precipitation_probability_percent: float | None
    precipitation_mm: float | None
    weather_code: int | None
    condition: str | None
    icon: str | None
    is_day: bool | None


class WeatherResponse(BaseModel):
    location: Location
    current: CurrentWeather
    hourly: list[HourlyForecast]
    source: str = "Open-Meteo"
    data_status: DataStatus = "model"
    fetched_at: datetime
    attribution: str


class CurrentAirQuality(BaseModel):
    time: str
    european_aqi: float | None
    european_aqi_label: str | None
    pm10_ugm3: float | None
    pm2_5_ugm3: float | None
    nitrogen_dioxide_ugm3: float | None
    ozone_ugm3: float | None


class AirQualityResponse(BaseModel):
    location: Location
    current: CurrentAirQuality
    source: str = "Open-Meteo Air Quality (CAMS Europe)"
    data_status: DataStatus = "model"
    fetched_at: datetime
    attribution: str
