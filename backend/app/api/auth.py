"""Account endpoints: register, log in, and "who am I"."""

from typing import Annotated

import psycopg
from fastapi import APIRouter, Depends, HTTPException
from psycopg import Connection

from app.api.deps import CurrentUser, get_settings
from app.config import Settings
from app.db import get_connection
from app.repositories import users as repo
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

ConnDep = Annotated[Connection, Depends(get_connection)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def _token_response(settings: Settings, user: dict) -> TokenResponse:
    token, expires_in = create_access_token(settings, user["id"], user["role"])
    return TokenResponse(access_token=token, expires_in=expires_in, user=UserOut(**user))


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(body: RegisterRequest, conn: ConnDep, settings: SettingsDep) -> TokenResponse:
    """Create a normal user account (role `user`) and log it in."""
    if repo.email_exists(conn, body.email):
        raise HTTPException(409, "An account with this e-mail already exists")
    try:
        user = repo.create(conn, body.email, hash_password(body.password))
    except psycopg.errors.UniqueViolation:  # two sign-ups at the same moment
        raise HTTPException(409, "An account with this e-mail already exists") from None
    repo.touch_last_login(conn, user["id"])
    return _token_response(settings, user)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, conn: ConnDep, settings: SettingsDep) -> TokenResponse:
    """Exchange e-mail + password for a bearer token."""
    user = repo.get_by_email_with_hash(conn, body.email)
    # Same message whether the e-mail is unknown or the password is wrong.
    if not verify_password(body.password, user["password_hash"] if user else None):
        raise HTTPException(401, "Incorrect e-mail or password")
    if not user["is_active"]:
        raise HTTPException(403, "This account has been deactivated")
    repo.touch_last_login(conn, user["id"])
    user = repo.get_by_id(conn, user["id"])
    return _token_response(settings, user)


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> UserOut:
    """The account that owns the token."""
    return UserOut(**user)
