"""Request and response models for login and the admin dashboard."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.meta import FeedInfo

Role = Literal["user", "admin"]
# Deliberately simple check: something@something.something (no extra dependency needed).
EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class Credentials(BaseModel):
    email: str = Field(max_length=254, pattern=EMAIL_PATTERN)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email", mode="before")
    @classmethod
    def normalise_email(cls, value: object) -> object:
        # Runs before the pattern check, so " Alice@Example.com " is accepted and stored lower-case.
        return value.strip().lower() if isinstance(value, str) else value


class LoginRequest(Credentials):
    pass


class RegisterRequest(Credentials):
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    """A user as returned by the API. Never contains the password hash."""

    id: int
    email: str
    role: Role
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int = Field(description="Token lifetime in seconds")
    user: UserOut


class UserUpdate(BaseModel):
    role: Role | None = None
    is_active: bool | None = None


class UserStats(BaseModel):
    total: int
    admins: int
    active: int
    new_last_7_days: int
    logins_last_7_days: int


class LayerImportStatus(BaseModel):
    id: str
    title: str
    feature_count: int
    imported_at: datetime | None


class DataStatus(BaseModel):
    feed: FeedInfo | None
    days_until_expiry: int | None = Field(
        description="Days until the timetable ends (negative = expired)"
    )
    layers: list[LayerImportStatus]
    realtime_enabled: bool


class AdminStats(BaseModel):
    users: UserStats
    stops: int
    routes: int
    trips_today: int
    urban_features: int
