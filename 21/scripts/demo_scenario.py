"""Сквозной демонстрационный сценарий работы системы (п. 30 методички).

Сценарий выполняется на изолированной базе SQLite во временном каталоге,
поэтому не изменяет рабочие данные приложения.

Запуск:
    python -m scripts.demo_scenario
"""
from __future__ import annotations

import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402

ADMIN_EMAIL = "admin@hotel.ru"
ADMIN_PASSWORD = "admin-pass-12345"
GUEST_PASSWORD = "guest-pass-12345"


def print_step(title: str) -> None:
    print(f"\n=== {title} ===")


def run_scenario(app: FastAPI) -> None:
    with TestClient(app) as client:
        print_step("1. Проверка работоспособности сервиса")
        print(client.get("/health").json())

        print_step("2. Регистрация и вход гостя")
        register = client.post(
            "/auth/register",
            json={
                "email": "guest@example.com",
                "full_name": "Иван Петров",
                "password": GUEST_PASSWORD,
            },
        )
        print("регистрация:", register.status_code, register.json()["role"])
        login = client.post(
            "/auth/login",
            json={"email": "guest@example.com", "password": GUEST_PASSWORD},
        )
        guest_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        print("вход гостя:", login.status_code)

        admin_login = client.post(
            "/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
        print("вход администратора:", admin_login.status_code)

        print_step("3. Администратор добавляет номера")
        rooms = []
        for payload in (
            {
                "number": "101",
                "room_type": "standard",
                "capacity": 2,
                "price_per_night": 4500,
                "floor": 1,
            },
            {
                "number": "502",
                "room_type": "lux",
                "capacity": 4,
                "price_per_night": 12000,
                "floor": 5,
            },
        ):
            response = client.post("/rooms", json=payload, headers=admin_headers)
            rooms.append(response.json())
            print("номер:", response.status_code, response.json()["number"])
        room_id = rooms[0]["id"]
        forbidden = client.post(
            "/rooms",
            json={"number": "777", "capacity": 2, "price_per_night": 5000},
            headers=guest_headers,
        )
        print("отказ гостю в создании номера:", forbidden.status_code)

        check_in = date.today() + timedelta(days=3)
        check_out = check_in + timedelta(days=4)

        print_step("4. Поиск свободных номеров на период")
        available = client.get(
            "/rooms/available",
            params={"check_in": check_in.isoformat(), "check_out": check_out.isoformat()},
        )
        print("свободно номеров:", len(available.json()))

        print_step("5. Создание бронирования и проверка пересечения периодов")
        booking = client.post(
            "/bookings",
            json={
                "room_id": room_id,
                "check_in": check_in.isoformat(),
                "check_out": check_out.isoformat(),
                "comment": "Тихий номер",
            },
            headers=guest_headers,
        )
        print("бронирование:", booking.status_code, booking.json())
        conflict = client.post(
            "/bookings",
            json={
                "room_id": room_id,
                "check_in": (check_in + timedelta(days=1)).isoformat(),
                "check_out": (check_out + timedelta(days=1)).isoformat(),
            },
            headers=admin_headers,
        )
        print("пересечение периодов:", conflict.status_code, conflict.json()["error"])
        booking_id = booking.json()["id"]

        print_step("6. Оплата бронирования (частичная и полная)")
        partial = client.post(
            "/payments",
            json={"booking_id": booking_id, "amount": 5000, "method": "card"},
            headers=guest_headers,
        )
        print("частичная оплата:", partial.status_code, partial.json()["amount"])
        overpay = client.post(
            "/payments",
            json={"booking_id": booking_id, "amount": 999999, "method": "card"},
            headers=guest_headers,
        )
        print("превышение суммы:", overpay.status_code, overpay.json()["error"])
        remainder = client.get(f"/bookings/{booking_id}", headers=guest_headers).json()
        print("остаток к оплате:", remainder["remaining_amount"])
        final = client.post(
            "/payments",
            json={
                "booking_id": booking_id,
                "amount": remainder["remaining_amount"],
                "method": "transfer",
            },
            headers=guest_headers,
        )
        print("закрывающий платёж:", final.status_code)

        print_step("7. Завершение проживания и статистика")
        completed = client.post(f"/bookings/{booking_id}/complete", headers=admin_headers)
        print("статус бронирования:", completed.json()["status"])
        summary = client.get("/reports/summary", headers=admin_headers)
        print("сводка:", summary.json())

        print_step("8. Обработка некорректных данных")
        bad_date = client.post(
            "/bookings",
            json={
                "room_id": room_id,
                "check_in": check_out.isoformat(),
                "check_out": check_in.isoformat(),
            },
            headers=guest_headers,
        )
        print("некорректный период:", bad_date.status_code, bad_date.json()["error"])
        unknown_room = client.get("/rooms/9999")
        print("несуществующий номер:", unknown_room.status_code, unknown_room.json()["error"])
        anonymous = client.get("/bookings")
        print("без токена:", anonymous.status_code, anonymous.json()["error"])


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        settings = Settings(
            database_url=f"sqlite:///{Path(tmp) / 'demo.db'}",
            jwt_secret="demo-secret-demo-secret-demo-secret",
            admin_email=ADMIN_EMAIL,
            admin_password=ADMIN_PASSWORD,
            log_level="WARNING",
        )
        app = create_app(settings)
        try:
            run_scenario(app)
        finally:
            app.state.engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
