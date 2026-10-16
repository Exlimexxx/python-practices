"""Тесты служебных маршрутов и авторизации."""
from __future__ import annotations

import pytest

from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD, GUEST_EMAIL, GUEST_PASSWORD
from tests.helpers import register_and_login


def test_health_reports_healthy(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["service"]


def test_openapi_documentation_is_available(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/bookings" in paths
    assert "/rooms/available" in paths
    assert "/reports/summary" in paths


def test_register_creates_guest_with_user_role(client):
    response = client.post(
        "/auth/register",
        json={"email": "newbie@example.com", "full_name": "Новый Гость", "password": "newbie-pass-1"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["role"] == "user"
    assert body["is_active"] is True
    assert "password" not in body and "password_hash" not in body


def test_register_rejects_duplicate_email(client, guest):
    response = client.post(
        "/auth/register",
        json={"email": GUEST_EMAIL.upper(), "full_name": "Дубль", "password": GUEST_PASSWORD},
    )
    assert response.status_code == 409
    assert response.json()["error"] == "EMAIL_ALREADY_USED"


@pytest.mark.parametrize(
    "email",
    ["not-an-email", "user@", "user@hotel.local", "user@@example.com"],
)
def test_register_rejects_invalid_email(client, email):
    response = client.post(
        "/auth/register",
        json={"email": email, "full_name": "Плохой Email", "password": "valid-pass-123"},
    )
    assert response.status_code == 422
    assert response.json()["error"] == "VALIDATION_ERROR"


@pytest.mark.parametrize("password", ["short", ""])
def test_register_rejects_weak_password(client, password):
    response = client.post(
        "/auth/register",
        json={"email": "weak@example.com", "full_name": "Слабый Пароль", "password": password},
    )
    assert response.status_code == 422


def test_login_returns_jwt_token(client, guest):
    response = client.post(
        "/auth/login", json={"email": GUEST_EMAIL, "password": GUEST_PASSWORD}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 30 * 60
    assert body["role"] == "user"
    assert body["access_token"].count(".") == 2


def test_login_with_wrong_password_returns_401(client, guest):
    response = client.post(
        "/auth/login", json={"email": GUEST_EMAIL, "password": "wrong-password-1"}
    )
    assert response.status_code == 401
    assert response.json()["error"] == "AUTHENTICATION_FAILED"


def test_login_with_unknown_email_returns_401(client):
    response = client.post(
        "/auth/login", json={"email": "nobody@example.com", "password": "any-password-1"}
    )
    assert response.status_code == 401


def test_me_returns_current_user(client, guest):
    response = client.get("/auth/me", headers=guest["headers"])
    assert response.status_code == 200
    assert response.json()["id"] == guest["id"]


def test_me_requires_token(client):
    response = client.get("/auth/me")
    assert response.status_code == 401
    assert response.json()["error"] == "AUTHENTICATION_FAILED"


def test_me_rejects_broken_token(client):
    response = client.get("/auth/me", headers={"Authorization": "Bearer not.a.token"})
    assert response.status_code == 401


def test_admin_can_list_and_create_users(client, admin):
    listing = client.get("/users", headers=admin["headers"])
    assert listing.status_code == 200
    assert listing.json()["total"] >= 1

    created = client.post(
        "/users",
        json={
            "email": "manager@example.com",
            "full_name": "Менеджер Отеля",
            "password": "manager-pass-1",
            "role": "admin",
        },
        headers=admin["headers"],
    )
    assert created.status_code == 201
    assert created.json()["role"] == "admin"

    login = client.post(
        "/auth/login", json={"email": "manager@example.com", "password": "manager-pass-1"}
    )
    assert login.status_code == 200
    assert login.json()["role"] == "admin"


def test_guest_has_no_access_to_user_management(client, guest):
    assert client.get("/users", headers=guest["headers"]).status_code == 403
    assert client.get(f"/users/{guest['id']}", headers=guest["headers"]).status_code == 403


def test_unknown_user_returns_404(client, admin):
    response = client.get("/users/999", headers=admin["headers"])
    assert response.status_code == 404
    assert response.json()["error"] == "USER_NOT_FOUND"


def test_registered_guest_can_login(client):
    created = register_and_login(
        client, email="second-way@example.com", password="second-pass-123"
    )
    assert created["id"] > 0
    assert ADMIN_EMAIL != created["email"]
    assert ADMIN_PASSWORD != created["password"]
