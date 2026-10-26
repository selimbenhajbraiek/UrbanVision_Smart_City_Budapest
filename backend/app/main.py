"""FastAPI application factory. Run with: uvicorn app.main:app --reload"""

import logging
from contextlib import asynccontextmanager

import psycopg
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from psycopg_pool import PoolTimeout

from app.api import api_router
from app.config import Settings, get_settings
from app.db import create_pool
from app.errors import FeatureNotConfiguredError, UpstreamServiceError
from app.logging_config import setup_logging
from app.realtime import create_realtime_provider
from app.services.weather import WeatherService

logger = logging.getLogger(__name__)

DESCRIPTION = """
REST API of **UrbanVision**, an interactive smart-city map of Budapest.

* Public transport: BKK GTFS timetable (**scheduled** data, not real-time)
* Weather & air quality: Open-Meteo (model data)
* Urban layers: OpenStreetMap snapshots (static)
* Real-time vehicles/alerts: optional, requires a BKK API key
"""


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    setup_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.pool = create_pool(settings.database_url())
        app.state.weather = WeatherService(settings)
        app.state.realtime = create_realtime_provider(settings)
        logger.info("UrbanVision API started (real-time: %s)", app.state.realtime.enabled)
        yield
        app.state.pool.close()
        app.state.weather.close()
        app.state.realtime.close()

    app = FastAPI(
        title="UrbanVision API", version="1.0.0", description=DESCRIPTION, lifespan=lifespan
    )
    app.state.settings = settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["GET"],
        allow_headers=["*"],
    )
    app.add_middleware(GZipMiddleware, minimum_size=1024)  # GeoJSON compresses ~10x

    _register_error_handlers(app)
    app.include_router(api_router)
    return app


def _register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(UpstreamServiceError)
    async def upstream_error(_: Request, exc: UpstreamServiceError) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": str(exc)})

    @app.exception_handler(FeatureNotConfiguredError)
    async def not_configured(_: Request, exc: FeatureNotConfiguredError) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": str(exc)})

    @app.exception_handler(psycopg.errors.UndefinedTable)
    async def schema_missing(_: Request, exc: Exception) -> JSONResponse:
        logger.error("Database schema missing: %s", exc)
        return JSONResponse(
            status_code=503,
            content={"detail": "Database is not initialised. Run `python -m ingestion gtfs`."},
        )

    @app.exception_handler(PoolTimeout)
    @app.exception_handler(psycopg.OperationalError)
    async def database_down(_: Request, exc: Exception) -> JSONResponse:
        logger.error("Database unavailable: %s", exc)
        return JSONResponse(status_code=503, content={"detail": "Database is unavailable"})


app = create_app()
