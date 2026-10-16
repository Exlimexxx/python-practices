"""Вспомогательные функции для тестов: данные запросов и авторизация."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from fastapi.testclient import TestClient

DEFAULT_ROOM_PRICE = 4500.0


def future_period(offset_days: int = 3, nights: int = 4) -> tuple[date, date]:
    check_in = date.today() + timedelta(days=offset_days)
    return check_in, check_in + timedelta(days=nights)


def period_payload(check_in: date, check_out: date) -> dict[str, str]:
    return {"check_in": check_in.isoformat(), "check_out": check_out.isoformat()}


def room_payload(number: str = "101", **overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "number": number,
        "room_type": "standard",
        "capacity": 2,
        "price_per_night": DEFAULT_ROOM_PRICE,
        "floor": 1,
    }
    payload.update(overrides)
    return payload


def booking_payload(room_id: int, check_in: date, check_out: date, **overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"room_id": room_id, **period_payload(check_in, check_out)}
    payload.update(overrides)
    return payload


def payment_payload(booking_id: int, amount: float, method: str = "card") -> dict[str, Any]:
    return {"booking_id": booking_id, "amount": amount, "method": method}


def register_and_login(
    client: TestClient,
    *,
    email: str,
    password: str,
    full_name: str = "Иван Петров",
) -> dict[str, Any]:
    """Зарегистрировать пользователя и вернуть его данные вместе с заголовками."""
    register = client.post(
        "/auth/register", json={"email": email, "full_name": full_name, "password": password}
    )
    assert register.status_code == 201, register.text
    login = client.post("/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    return {
        "id": register.json()["id"],
        "email": email,
        "password": password,
        "headers": {"Authorization": f"Bearer {login.json()['access_token']}"},
    }


def make_room(
    client: TestClient, admin_headers: dict[str, str], number: str, **overrides: Any
) -> dict[str, Any]:
    """Создать номер администратором и вернуть его представление."""
    response = client.post(
        "/rooms", json=room_payload(number, **overrides), headers=admin_headers
    )
    assert response.status_code == 201, response.text
    return response.json()


def today_plus(days: int) -> date:
    return date.today() + timedelta(days=days)
