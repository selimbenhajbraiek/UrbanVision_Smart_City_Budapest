"""Admin dashboard endpoints: access control, user management, data status."""

import pytest

from app.repositories import users as users_repo
from app.security import hash_password
from ingestion.__main__ import main as cli

PASSWORD = "correct-horse-battery"


@pytest.fixture(autouse=True)
def clean_users(db):
    db.execute("TRUNCATE users RESTART IDENTITY")
    yield
    db.execute("TRUNCATE users RESTART IDENTITY")


def login(client, email: str) -> dict:
    token = client.post("/api/auth/login", json={"email": email, "password": PASSWORD}).json()[
        "access_token"
    ]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(client, db):
    users_repo.create(db, "admin@example.com", hash_password(PASSWORD), role="admin")
    return login(client, "admin@example.com")


@pytest.fixture
def user_headers(client, db):
    users_repo.create(db, "user@example.com", hash_password(PASSWORD))
    return login(client, "user@example.com")


ADMIN_GETS = ["/api/admin/stats", "/api/admin/users", "/api/admin/data-status"]


@pytest.mark.parametrize("path", ADMIN_GETS)
def test_admin_routes_require_login(client, path):
    assert client.get(path).status_code == 401


@pytest.mark.parametrize("path", ADMIN_GETS)
def test_admin_routes_forbidden_for_normal_users(client, user_headers, path):
    assert client.get(path, headers=user_headers).status_code == 403


def test_admin_stats(client, admin_headers, user_headers):
    body = client.get("/api/admin/stats", headers=admin_headers).json()
    assert body["users"]["total"] == 2
    assert body["users"]["admins"] == 1
    assert body["users"]["logins_last_7_days"] == 2
    assert body["routes"] == 4  # mini GTFS feed


def test_data_status(client, admin_headers):
    body = client.get("/api/admin/data-status", headers=admin_headers).json()
    assert body["feed"]["feed_version"]
    assert isinstance(body["days_until_expiry"], int)
    assert {layer["id"] for layer in body["layers"]} >= {"ev_charging", "park_and_ride"}
    assert body["realtime_enabled"] is False


def test_list_users_never_exposes_password_hash(client, admin_headers, user_headers):
    users = client.get("/api/admin/users", headers=admin_headers).json()
    assert [u["email"] for u in users] == ["admin@example.com", "user@example.com"]
    assert all("password_hash" not in u for u in users)


def test_promote_and_deactivate_user(client, admin_headers, user_headers, db):
    user_id = db.execute("SELECT id FROM users WHERE role = 'user'").fetchone()["id"]
    promoted = client.patch(
        f"/api/admin/users/{user_id}", json={"role": "admin"}, headers=admin_headers
    )
    assert promoted.status_code == 200 and promoted.json()["role"] == "admin"
    deactivated = client.patch(
        f"/api/admin/users/{user_id}", json={"is_active": False}, headers=admin_headers
    )
    assert deactivated.json()["is_active"] is False
    # the deactivated user's existing token stops working immediately
    assert client.get("/api/auth/me", headers=user_headers).status_code == 401


def test_admin_cannot_lock_themselves_out(client, admin_headers, db):
    admin_id = db.execute("SELECT id FROM users").fetchone()["id"]
    for body in ({"role": "user"}, {"is_active": False}):
        response = client.patch(f"/api/admin/users/{admin_id}", json=body, headers=admin_headers)
        assert response.status_code == 409
    assert client.delete(f"/api/admin/users/{admin_id}", headers=admin_headers).status_code == 409


def test_delete_user(client, admin_headers, user_headers, db):
    user_id = db.execute("SELECT id FROM users WHERE role = 'user'").fetchone()["id"]
    assert client.delete(f"/api/admin/users/{user_id}", headers=admin_headers).status_code == 204
    assert client.delete(f"/api/admin/users/{user_id}", headers=admin_headers).status_code == 404


def test_invalid_role_is_rejected(client, admin_headers, user_headers, db):
    user_id = db.execute("SELECT id FROM users WHERE role = 'user'").fetchone()["id"]
    response = client.patch(
        f"/api/admin/users/{user_id}", json={"role": "superuser"}, headers=admin_headers
    )
    assert response.status_code == 422


def test_create_admin_command(client, db):
    assert (
        cli(["--test-db", "create-admin", "--email", "Boss@Example.com", "--password", PASSWORD])
        == 0
    )
    row = db.execute("SELECT email, role FROM users").fetchone()
    assert row == {"email": "boss@example.com", "role": "admin"}
    assert (
        client.get("/api/admin/users", headers=login(client, "boss@example.com")).status_code == 200
    )
    # running it again promotes/resets instead of failing
    assert (
        cli(["--test-db", "create-admin", "--email", "boss@example.com", "--password", PASSWORD])
        == 0
    )
    assert (
        cli(["--test-db", "create-admin", "--email", "x@example.com", "--password", "short"]) == 1
    )
