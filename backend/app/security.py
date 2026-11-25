"""Password hashing (Argon2) and login tokens (JWT, HS256).

Passwords are never stored or logged in clear text. A token only carries the user id
and role; every protected request re-reads the user from the database, so a deleted,
deactivated or demoted user loses access immediately.
"""

from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

from app.config import Settings
from app.errors import FeatureNotConfiguredError

ALGORITHM = "HS256"
_password_hash = PasswordHash.recommended()  # Argon2id with safe defaults
# Used when the e-mail does not exist, so a failed login takes the same time either way.
_DUMMY_HASH = _password_hash.hash("not-a-real-password")


class InvalidTokenError(Exception):
    """The token is missing, malformed, tampered with or expired."""


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    if password_hash is None:
        _password_hash.verify(password, _DUMMY_HASH)
        return False
    return _password_hash.verify(password, password_hash)


def _secret(settings: Settings) -> str:
    if settings.jwt_secret_key is None or not settings.jwt_secret_key.get_secret_value().strip():
        raise FeatureNotConfiguredError(
            "Login is not configured. Set JWT_SECRET_KEY in .env and restart the backend."
        )
    return settings.jwt_secret_key.get_secret_value()


def create_access_token(settings: Settings, user_id: int, role: str) -> tuple[str, int]:
    """Return (token, lifetime in seconds)."""
    lifetime = timedelta(minutes=settings.jwt_expire_minutes)
    now = datetime.now(UTC)
    payload = {"sub": str(user_id), "role": role, "iat": now, "exp": now + lifetime}
    return jwt.encode(payload, _secret(settings), algorithm=ALGORITHM), int(
        lifetime.total_seconds()
    )


def decode_token(settings: Settings, token: str) -> int:
    """Return the user id stored in a valid token."""
    try:
        payload = jwt.decode(
            token, _secret(settings), algorithms=[ALGORITHM], options={"require": ["exp", "sub"]}
        )
        return int(payload["sub"])
    except (jwt.InvalidTokenError, ValueError) as exc:
        raise InvalidTokenError(str(exc)) from exc
