"""Register, login, tokens and /api/auth/me."""

from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.security import hash_password, verify_password

PASSWORD = "correct-horse-battery"


@pytest.fixture(autouse=True)
def clean_users(db):
    db.execute("TRUNCATE users RESTART IDENTITY")
    yield
    db.execute("TRUNCATE users RESTART IDENTITY")


def register(client, email="alice@example.com", password=PASSWORD):
    return client.post("/api/auth/register", json={"email": email, "password": password})


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_password_is_hashed_not_stored_in_clear():
    hashed = hash_password(PASSWORD)
    assert PASSWORD not in hashed and hashed.startswith("$argon2")
    assert verify_password(PASSWORD, hashed)
    assert not verify_password("wrong-password", hashed)
    assert not verify_password(PASSWORD, None)


def test_register_creates_user_and_returns_token(client, db):
    response = register(client, email="  Alice@Example.COM ")
    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer" and body["expires_in"] == 3600
    assert body["user"]["email"] == "alice@example.com"  # normalised
    assert body["user"]["role"] == "user"
    assert "password_hash" not in body["user"]
    stored = db.execute("SELECT password_hash FROM users").fetchone()["password_hash"]
    assert stored.startswith("$argon2")


def test_register_duplicate_email_returns_409(client):
    register(client)
    assert register(client, email="ALICE@example.com").status_code == 409


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "not-an-email", "password": PASSWORD},
        {"email": "bob@example.com", "password": "short"},
        {"email": "bob@example.com"},
    ],
)
def test_register_validation_errors(client, payload):
    assert client.post("/api/auth/register", json=payload).status_code == 422


def test_login_success_and_me(client):
    register(client)
    response = client.post(
        "/api/auth/login", json={"email": "alice@example.com", "password": PASSWORD}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    me = client.get("/api/auth/me", headers=auth(token))
    assert me.status_code == 200
    assert me.json()["email"] == "alice@example.com"
    assert me.json()["last_login_at"] is not None


def test_login_errors_do_not_reveal_whether_email_exists(client):
    register(client)
    wrong_password = client.post(
        "/api/auth/login", json={"email": "alice@example.com", "password": "nope-nope"}
    )
    unknown_email = client.post(
        "/api/auth/login", json={"email": "nobody@example.com", "password": PASSWORD}
    )
    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


def test_me_requires_a_valid_token(client, settings):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers=auth("garbage")).status_code == 401
    forged = jwt.encode(
        {"sub": "1", "exp": datetime.now(UTC) + timedelta(hours=1)},
        "a-different-secret-key-that-is-long-enough-for-hs256",
        algorithm="HS256",
    )
    assert client.get("/api/auth/me", headers=auth(forged)).status_code == 401


def test_expired_token_is_rejected(client, settings):
    user_id = register(client).json()["user"]["id"]
    expired = jwt.encode(
        {"sub": str(user_id), "exp": datetime.now(UTC) - timedelta(minutes=1)},
        settings.jwt_secret_key.get_secret_value(),
        algorithm="HS256",
    )
    assert client.get("/api/auth/me", headers=auth(expired)).status_code == 401


def test_deactivated_user_cannot_log_in_or_use_old_token(client, db):
    token = register(client).json()["access_token"]
    db.execute("UPDATE users SET is_active = FALSE")
    assert client.get("/api/auth/me", headers=auth(token)).status_code == 401
    response = client.post(
        "/api/auth/login", json={"email": "alice@example.com", "password": PASSWORD}
    )
    assert response.status_code == 403
