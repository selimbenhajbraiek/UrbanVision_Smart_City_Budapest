from typing import Annotated

from fastapi import APIRouter, Query, Request

from app.api.deps import resolve_location
from app.schemas.weather import AirQualityResponse, WeatherResponse
from app.services.weather import WeatherService

router = APIRouter(tags=["weather"])

Lat = Annotated[float | None, Query(ge=-90, le=90, description="Default: central Budapest")]
Lon = Annotated[float | None, Query(ge=-180, le=180, description="Default: central Budapest")]


def _service(request: Request) -> WeatherService:
    return request.app.state.weather


@router.get("/weather", response_model=WeatherResponse)
def get_weather(request: Request, lat: Lat = None, lon: Lon = None) -> WeatherResponse:
    """Current weather and a 12-hour forecast from Open-Meteo (model data, cached 10 min)."""
    return _service(request).get_weather(*resolve_location(lat, lon))


@router.get("/air-quality", response_model=AirQualityResponse)
def get_air_quality(request: Request, lat: Lat = None, lon: Lon = None) -> AirQualityResponse:
    """Current European Air Quality Index and pollutants (Open-Meteo / CAMS model data)."""
    return _service(request).get_air_quality(*resolve_location(lat, lon))
