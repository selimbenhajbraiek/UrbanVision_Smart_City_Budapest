"""Application configuration, loaded from environment variables and the project-root `.env`."""

from functools import lru_cache
from pathlib import Path
from urllib.parse import quote

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent

# Central Budapest (Deák Ferenc tér) — default location for weather / map centre.
BUDAPEST_CENTER = (47.4979, 19.0402)
# Rough bounding box of Budapest and its immediate surroundings (lat/lon).
BUDAPEST_BOUNDS = {"min_lat": 47.30, "max_lat": 47.70, "min_lon": 18.85, "max_lon": 19.35}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Database
    postgres_user: str = "urbanvision"
    postgres_password: SecretStr
    postgres_host: str = "localhost"
    postgres_port: int = 5433
    postgres_db: str = "urbanvision"
    postgres_test_db: str = "urbanvision_test"

    # API
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    timezone: str = "Europe/Budapest"

    # Data sources
    gtfs_url: str = "https://bkk.hu/gtfs/budapest_gtfs.zip"
    gtfs_download_dir: Path = BACKEND_DIR / "data" / "gtfs"
    open_meteo_forecast_url: str = "https://api.open-meteo.com/v1/forecast"
    open_meteo_air_quality_url: str = "https://air-quality-api.open-meteo.com/v1/air-quality"
    weather_cache_ttl_seconds: int = 600
    http_timeout_seconds: float = 10.0
    overpass_url: str = "https://overpass-api.de/api/interpreter"

    # Real-time (optional, Phase 10)
    bkk_api_key: SecretStr | None = None
    bkk_realtime_base_url: str = "https://go.bkk.hu/api/query/v1/ws/gtfs-rt/full"
    realtime_cache_ttl_seconds: int = 15

    # Identifies us to public APIs (required by the Overpass / OSM usage policies).
    user_agent: str = "UrbanVision/1.0 (university smart-city project)"

    def database_url(self, database: str | None = None) -> str:
        password = quote(self.postgres_password.get_secret_value(), safe="")
        return (
            f"postgresql://{quote(self.postgres_user, safe='')}:{password}"
            f"@{self.postgres_host}:{self.postgres_port}/{database or self.postgres_db}"
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def realtime_enabled(self) -> bool:
        return bool(self.bkk_api_key and self.bkk_api_key.get_secret_value().strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()
