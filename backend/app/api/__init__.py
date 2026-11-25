from fastapi import APIRouter

from . import admin, auth, health, layers, meta, planner, realtime, routes, search, stops, weather

api_router = APIRouter(prefix="/api")
for module in (
    health,
    meta,
    stops,
    routes,
    search,
    planner,
    weather,
    layers,
    realtime,
    auth,
    admin,
):
    api_router.include_router(module.router)
