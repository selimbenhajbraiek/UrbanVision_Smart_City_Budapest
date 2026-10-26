from fastapi import APIRouter

from . import health, layers, meta, realtime, routes, search, stops, weather

api_router = APIRouter(prefix="/api")
for module in (health, meta, stops, routes, search, weather, layers, realtime):
    api_router.include_router(module.router)
