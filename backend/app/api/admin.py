"""Admin dashboard endpoints. Every route requires a logged-in admin (403 otherwise)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from psycopg import Connection

from app.api.deps import AdminUser, get_settings, local_now, require_admin
from app.api.meta import feed_info
from app.config import Settings
from app.db import get_connection
from app.repositories import meta as meta_repo
from app.repositories import urban_layers as layers_repo
from app.repositories import users as repo
from app.schemas.auth import (
    AdminStats,
    DataStatus,
    LayerImportStatus,
    UserOut,
    UserStats,
    UserUpdate,
)
from app.urban_layers import URBAN_LAYERS

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])

ConnDep = Annotated[Connection, Depends(get_connection)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


@router.get("/stats", response_model=AdminStats)
def stats(conn: ConnDep, settings: SettingsDep) -> AdminStats:
    """User figures plus the main data figures."""
    counts = meta_repo.transit_counts(conn, local_now(settings).date())
    return AdminStats(
        users=UserStats(**repo.stats(conn)),
        stops=counts["stops"],
        routes=counts["routes"],
        trips_today=counts["trips_today"],
        urban_features=counts["urban_features"],
    )


@router.get("/data-status", response_model=DataStatus)
def data_status(request: Request, conn: ConnDep, settings: SettingsDep) -> DataStatus:
    """Is the timetable still valid, and when were the OpenStreetMap layers imported?"""
    today = local_now(settings).date()
    feed = feed_info(conn, today)
    imports = layers_repo.layer_imports(conn)
    return DataStatus(
        feed=feed,
        days_until_expiry=(feed.valid_to - today).days if feed and feed.valid_to else None,
        layers=[
            LayerImportStatus(
                id=layer.id,
                title=layer.title,
                feature_count=imports[layer.id]["feature_count"] if layer.id in imports else 0,
                imported_at=imports[layer.id]["imported_at"] if layer.id in imports else None,
            )
            for layer in URBAN_LAYERS.values()
        ],
        realtime_enabled=request.app.state.realtime.enabled,
    )


@router.get("/users", response_model=list[UserOut])
def list_users(conn: ConnDep) -> list[UserOut]:
    return [UserOut(**u) for u in repo.list_all(conn)]


def _guard_last_admin(conn: Connection, target: dict, admin: dict, losing_admin: bool) -> None:
    """Never let the dashboard lock everyone out."""
    if not losing_admin or target["role"] != "admin":
        return
    if target["id"] == admin["id"]:
        raise HTTPException(409, "You cannot remove your own admin access")
    if repo.count_active_admins(conn) <= 1:
        raise HTTPException(409, "At least one active admin must remain")


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, body: UserUpdate, conn: ConnDep, admin: AdminUser) -> UserOut:
    """Change a user's role and/or activate / deactivate the account."""
    target = repo.get_by_id(conn, user_id)
    if target is None:
        raise HTTPException(404, f"User {user_id} not found")
    losing_admin = body.role == "user" or body.is_active is False
    _guard_last_admin(conn, target, admin, losing_admin)
    if target["id"] == admin["id"] and body.is_active is False:
        raise HTTPException(409, "You cannot deactivate your own account")
    return UserOut(**repo.update(conn, user_id, body.role, body.is_active))


@router.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: int, conn: ConnDep, admin: AdminUser) -> Response:
    target = repo.get_by_id(conn, user_id)
    if target is None:
        raise HTTPException(404, f"User {user_id} not found")
    if target["id"] == admin["id"]:
        raise HTTPException(409, "You cannot delete your own account")
    _guard_last_admin(conn, target, admin, losing_admin=True)
    repo.delete(conn, user_id)
    return Response(status_code=204)
