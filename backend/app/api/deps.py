"""Shared request helpers: settings access and validation of common query parameters."""

from datetime import datetime
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from psycopg import Connection

from app.config import BUDAPEST_BOUNDS, BUDAPEST_CENTER, Settings
from app.db import get_connection
from app.repositories import BBox
from app.repositories import users as users_repo
from app.security import InvalidTokenError, decode_token
from app.transport_modes import parse_modes

_bearer = HTTPBearer(auto_error=False)


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    conn: Annotated[Connection, Depends(get_connection)],
) -> dict:
    """The logged-in user (from `Authorization: Bearer <token>`), or 401."""
    unauthorized = HTTPException(
        401, "Not authenticated or session expired", headers={"WWW-Authenticate": "Bearer"}
    )
    if credentials is None:
        raise unauthorized
    try:
        user_id = decode_token(request.app.state.settings, credentials.credentials)
    except InvalidTokenError:
        raise unauthorized from None
    user = users_repo.get_by_id(conn, user_id)
    if user is None or not user["is_active"]:
        raise unauthorized
    return user


def require_admin(user: Annotated[dict, Depends(get_current_user)]) -> dict:
    """The logged-in user if they are an admin, otherwise 403."""
    if user["role"] != "admin":
        raise HTTPException(403, "Admin access required")
    return user


CurrentUser = Annotated[dict, Depends(get_current_user)]
AdminUser = Annotated[dict, Depends(require_admin)]


def local_timezone(settings: Settings) -> ZoneInfo:
    return ZoneInfo(settings.timezone)


def local_now(settings: Settings) -> datetime:
    return datetime.now(local_timezone(settings))


def parse_bbox(raw: str | None) -> BBox | None:
    """`minLon,minLat,maxLon,maxLat` (the order used by GeoJSON and most map libraries)."""
    if raw is None:
        return None
    try:
        min_lon, min_lat, max_lon, max_lat = (float(part) for part in raw.split(","))
    except ValueError as exc:
        raise HTTPException(422, "bbox must be 'minLon,minLat,maxLon,maxLat' (4 numbers)") from exc
    if not (-180 <= min_lon < max_lon <= 180 and -90 <= min_lat < max_lat <= 90):
        raise HTTPException(422, "bbox coordinates are out of range or in the wrong order")
    return BBox(min_lon, min_lat, max_lon, max_lat)


def parse_mode_param(raw: str | None) -> list[str] | None:
    try:
        return parse_modes(raw)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


def parse_csv_param(raw: str | None, max_items: int = 200) -> list[str] | None:
    if raw is None or not raw.strip():
        return None
    items = [item.strip() for item in raw.split(",") if item.strip()]
    if len(items) > max_items:
        raise HTTPException(422, f"At most {max_items} values are allowed")
    return items


def resolve_location(lat: float | None, lon: float | None) -> tuple[float, float]:
    """Default to central Budapest; custom points must lie in the Budapest area."""
    if lat is None and lon is None:
        return BUDAPEST_CENTER
    if lat is None or lon is None:
        raise HTTPException(422, "Provide both lat and lon, or neither")
    b = BUDAPEST_BOUNDS
    if not (b["min_lat"] <= lat <= b["max_lat"] and b["min_lon"] <= lon <= b["max_lon"]):
        raise HTTPException(422, "Location must be within the Budapest area")
    return lat, lon
