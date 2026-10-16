"""Модульные и интеграционные тесты приложения (pytest).

Запуск: python -m pytest -v  (из каталога work/practice15)
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Iterator

import pytest
from flask import Flask
from flask.testing import FlaskClient

from app import create_app
from app.exceptions import BookingConflictError, ValidationError
from app.services import BookingService, GuestService, RoomService


@pytest.fixture()
def app() -> Iterator[Flask]:
    """Свежее приложение на in-memory SQLite для каждого теста."""
    application = create_app(
        {
            "DATABASE_URL": "sqlite:///:memory:",
            "TESTING": True,
            "SEED_DEMO": False,
            "DEBUG": False,
            "LOG_LEVEL": "WARNING",
        }
    )
    yield application


@pytest.fixture()
def client(app: Flask) -> FlaskClient:
    """Тестовый HTTP-клиент Flask."""
    return app.test_client()


@pytest.fixture()
def services(app: Flask):
    """Сервисы, работающие в контексте приложения (для проверки бизнес-логики)."""
    with app.app_context():
        session = app.extensions["database"].get_session()
        yield {
            "rooms": RoomService(session),
            "guests": GuestService(session),
            "bookings": BookingService(session),
        }
        app.extensions["database"].remove_session()


def make_room(client: FlaskClient, **overrides) -> dict:
    """Создаёт номер через REST API и возвращает его представление."""
    payload = {
        "number": "101",
        "room_type": "Стандарт",
        "capacity": 2,
        "price_per_night": 4000.0,
        "floor": 1,
        "description": "Тестовый номер",
        "is_active": True,
    }
    payload.update(overrides)
    response = client.post("/api/rooms", json=payload)
    assert response.status_code == 201, response.get_json()
    return response.get_json()


def make_guest(client: FlaskClient, **overrides) -> dict:
    """Создаёт гостя через REST API."""
    payload = {
        "full_name": "Тестов Тест",
        "email": "test@example.com",
        "phone": "+7-000-000-00-00",
        "passport": "0000 000000",
        "city": "Москва",
    }
    payload.update(overrides)
    response = client.post("/api/guests", json=payload)
    assert response.status_code == 201, response.get_json()
    return response.get_json()


# -------------------------- Тесты HTML-интерфейса --------------------------


@pytest.mark.parametrize(
    "path",
    ["/", "/rooms", "/rooms/create", "/guests", "/guests/create", "/bookings", "/bookings/create"],
)
def test_html_pages_return_200(client: FlaskClient, path: str) -> None:
    """Основные HTML-страницы отдают 200 и HTML."""
    response = client.get(path)
    assert response.status_code == 200
    assert "text/html" in response.headers["Content-Type"]


def test_html_404_page(client: FlaskClient) -> None:
    """Неизвестный адрес отдаёт кастомную 404-страницу."""
    response = client.get("/rooms/9999")
    assert response.status_code == 404
    assert "Страница не найдена" in response.get_data(as_text=True)


def test_html_crud_room_flow(client: FlaskClient) -> None:
    """Полный HTML-CRUD номера: создание, просмотр, правка, удаление."""
    created = client.post(
        "/rooms/create",
        data={"number": "777", "room_type": "Люкс", "capacity": "3",
              "price_per_night": "9000", "floor": "7", "description": "Тест", "is_active": "1"},
        follow_redirects=True,
    )
    assert created.status_code == 200
    body = created.get_data(as_text=True)
    assert "Номер № 777" in body and "успешно создан" in body

    edited = client.post(
        "/rooms/1/edit",
        data={"number": "777", "room_type": "Комфорт", "capacity": "4",
              "price_per_night": "9500", "floor": "7", "description": "Обновлено", "is_active": "1"},
        follow_redirects=True,
    )
    assert "обновлён" in edited.get_data(as_text=True)

    deleted = client.post("/rooms/1/delete", follow_redirects=True)
    assert deleted.status_code == 200
    assert client.get("/api/rooms/1").status_code == 404


def test_html_validation_error_is_flashed(client: FlaskClient, services) -> None:
    """Некорректная форма возвращает 400 и сообщение об ошибке."""
    response = client.post("/rooms/create", data={"number": "", "room_type": "Стандарт"})
    assert response.status_code == 400
    assert "обязательно" in response.get_data(as_text=True)


# ------------------------------ REST API: CRUD ------------------------------


def test_api_index(client: FlaskClient) -> None:
    """Корневой эндпоинт API отдаёт JSON-описание."""
    response = client.get("/api")
    assert response.status_code == 200
    assert response.get_json()["resources"]["rooms"] == "/api/rooms"


def test_rooms_api_crud(client: FlaskClient) -> None:
    """CRUD номеров через REST API с корректными кодами."""
    room = make_room(client, number="101")
    assert room["id"] == 1
    assert room["price_per_night"] == 4000.0

    listing = client.get("/api/rooms")
    assert listing.status_code == 200
    assert listing.get_json()["count"] == 1

    single = client.get(f"/api/rooms/{room['id']}")
    assert single.status_code == 200
    assert single.get_json()["number"] == "101"

    updated = client.put(f"/api/rooms/{room['id']}", json={"price_per_night": 5555.0})
    assert updated.status_code == 200
    assert updated.get_json()["price_per_night"] == 5555.0

    patched = client.patch(f"/api/rooms/{room['id']}", json={"room_type": "Люкс"})
    assert patched.status_code == 200
    assert patched.get_json()["room_type"] == "Люкс"

    removed = client.delete(f"/api/rooms/{room['id']}")
    assert removed.status_code == 204
    assert client.get(f"/api/rooms/{room['id']}").status_code == 404


def test_guests_api_crud(client: FlaskClient) -> None:
    """CRUD гостей через REST API, включая проверку формата email."""
    guest = make_guest(client, email="guest@example.com")
    assert client.get(f"/api/guests/{guest['id']}").status_code == 200

    bad = client.post("/api/guests", json={"full_name": "X", "email": "wrong-email"})
    assert bad.status_code == 400
    assert bad.get_json()["error"] == "ValidationError"

    duplicate = client.post("/api/guests", json={"full_name": "Y", "email": "guest@example.com"})
    assert duplicate.status_code == 400

    assert client.delete(f"/api/guests/{guest['id']}").status_code == 204


def test_api_not_found_and_method_not_allowed(client: FlaskClient) -> None:
    """API отдаёт JSON на 404 и 405."""
    missing = client.get("/api/rooms/12345")
    assert missing.status_code == 404
    assert missing.is_json

    method = client.delete("/api/rooms")
    assert method.status_code == 405
    assert method.is_json


# --------------------- Бизнес-логика бронирования ---------------------


def test_booking_price_calculation(client: FlaskClient) -> None:
    """Стоимость = число ночей × цена за ночь."""
    room = make_room(client, price_per_night=5000.0)
    guest = make_guest(client)
    check_in = date.today() + timedelta(days=5)
    check_out = check_in + timedelta(days=3)
    response = client.post(
        "/api/bookings",
        json={"room_id": room["id"], "guest_id": guest["id"],
              "check_in": check_in.isoformat(), "check_out": check_out.isoformat(),
              "guests_count": 2},
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data["nights"] == 3
    assert data["total_price"] == 15000.0
    assert data["status"] == "confirmed"


def test_booking_overlap_conflict(client: FlaskClient) -> None:
    """Пересекающиеся даты отклоняются с кодом 409."""
    room = make_room(client)
    guest = make_guest(client)
    base = date.today() + timedelta(days=10)
    first = client.post(
        "/api/bookings",
        json={"room_id": room["id"], "guest_id": guest["id"],
              "check_in": base.isoformat(),
              "check_out": (base + timedelta(days=4)).isoformat()},
    )
    assert first.status_code == 201

    overlapping = client.post(
        "/api/bookings",
        json={"room_id": room["id"], "guest_id": guest["id"],
              "check_in": (base + timedelta(days=2)).isoformat(),
              "check_out": (base + timedelta(days=6)).isoformat()},
    )
    assert overlapping.status_code == 409
    payload = overlapping.get_json()
    assert payload["error"] == "BookingConflictError"
    assert payload["conflicts"][0]["id"] == first.get_json()["id"]


def test_booking_adjacent_dates_allowed(client: FlaskClient) -> None:
    """Соседние интервалы (выезд = заезд) не считаются пересечением."""
    room = make_room(client)
    guest = make_guest(client)
    base = date.today() + timedelta(days=20)
    first = client.post("/api/bookings", json={
        "room_id": room["id"], "guest_id": guest["id"],
        "check_in": base.isoformat(), "check_out": (base + timedelta(days=2)).isoformat()})
    second = client.post("/api/bookings", json={
        "room_id": room["id"], "guest_id": guest["id"],
        "check_in": (base + timedelta(days=2)).isoformat(),
        "check_out": (base + timedelta(days=5)).isoformat()})
    assert first.status_code == 201
    assert second.status_code == 201


def test_booking_validation_errors(client: FlaskClient) -> None:
    """Некорректные даты и превышение вместимости отдают 400."""
    room = make_room(client, capacity=2)
    guest = make_guest(client)
    base = date.today() + timedelta(days=30)

    wrong_dates = client.post("/api/bookings", json={
        "room_id": room["id"], "guest_id": guest["id"],
        "check_in": base.isoformat(), "check_out": base.isoformat()})
    assert wrong_dates.status_code == 400

    too_many = client.post("/api/bookings", json={
        "room_id": room["id"], "guest_id": guest["id"],
        "check_in": base.isoformat(), "check_out": (base + timedelta(days=1)).isoformat(),
        "guests_count": 5})
    assert too_many.status_code == 400
    assert "вмещает" in too_many.get_json()["message"].lower()


def test_booking_update_keeps_itself(client: FlaskClient) -> None:
    """При обновлении бронь не конфликтует сама с собой."""
    room = make_room(client)
    guest = make_guest(client)
    base = date.today() + timedelta(days=40)
    created = client.post("/api/bookings", json={
        "room_id": room["id"], "guest_id": guest["id"],
        "check_in": base.isoformat(), "check_out": (base + timedelta(days=2)).isoformat()}).get_json()

    updated = client.put(f"/api/bookings/{created['id']}", json={"guests_count": 2})
    assert updated.status_code == 200
    assert updated.get_json()["guests_count"] == 2


def test_availability_endpoint(client: FlaskClient) -> None:
    """Эндпоинт доступности сообщает о конфликтах и считает стоимость."""
    room = make_room(client, price_per_night=3000.0)
    guest = make_guest(client)
    base = date.today() + timedelta(days=50)
    client.post("/api/bookings", json={
        "room_id": room["id"], "guest_id": guest["id"],
        "check_in": base.isoformat(), "check_out": (base + timedelta(days=3)).isoformat()})

    busy = client.get(f"/api/rooms/{room['id']}/availability",
                      query_string={"check_in": base.isoformat(),
                                    "check_out": (base + timedelta(days=1)).isoformat()})
    assert busy.status_code == 200
    assert busy.get_json()["available"] is False

    free = client.get(f"/api/rooms/{room['id']}/availability",
                      query_string={"check_in": (base + timedelta(days=3)).isoformat(),
                                    "check_out": (base + timedelta(days=5)).isoformat()})
    assert free.get_json()["available"] is True
    assert free.get_json()["estimated_price"] == 6000.0


def test_booking_cancel_releases_dates(client: FlaskClient) -> None:
    """После отмены брони даты снова доступны."""
    room = make_room(client)
    guest = make_guest(client)
    base = date.today() + timedelta(days=60)
    payload = {"room_id": room["id"], "guest_id": guest["id"],
               "check_in": base.isoformat(), "check_out": (base + timedelta(days=2)).isoformat()}
    first = client.post("/api/bookings", json=payload).get_json()
    assert client.post(f"/api/bookings/{first['id']}/cancel").status_code == 200
    assert client.post("/api/bookings", json=payload).status_code == 201


# --------------------- Поиск, фильтрация и сортировка ---------------------


def test_rooms_search_filter_sort(client: FlaskClient) -> None:
    """Поиск по описанию, фильтр по типу и сортировка по цене."""
    make_room(client, number="101", room_type="Стандарт", price_per_night=3000.0,
              description="Вид во двор")
    make_room(client, number="202", room_type="Люкс", price_per_night=12000.0,
              description="Панорамное окно")
    make_room(client, number="303", room_type="Люкс", price_per_night=9000.0,
              description="С балконом", is_active=False)

    search = client.get("/api/rooms", query_string={"search": "Панорамное"}).get_json()
    assert search["count"] == 1 and search["items"][0]["number"] == "202"

    by_type = client.get("/api/rooms", query_string={"room_type": "Люкс"}).get_json()
    assert by_type["count"] == 2

    active = client.get("/api/rooms", query_string={"is_active": "0"}).get_json()
    assert active["count"] == 1 and active["items"][0]["number"] == "303"

    sorted_desc = client.get("/api/rooms",
                             query_string={"sort": "price", "order": "desc"}).get_json()
    assert [item["number"] for item in sorted_desc["items"]] == ["202", "303", "101"]

    by_capacity = client.get("/api/rooms", query_string={"min_capacity": 2}).get_json()
    assert by_capacity["count"] >= 1


def test_bookings_filter_by_status_and_dates(client: FlaskClient) -> None:
    """Фильтрация броней по статусу и периоду."""
    room = make_room(client)
    guest = make_guest(client)
    base = date.today() + timedelta(days=80)
    client.post("/api/bookings", json={
        "room_id": room["id"], "guest_id": guest["id"],
        "check_in": base.isoformat(), "check_out": (base + timedelta(days=2)).isoformat()})
    cancelled = client.post("/api/bookings", json={
        "room_id": room["id"], "guest_id": guest["id"],
        "check_in": (base + timedelta(days=10)).isoformat(),
        "check_out": (base + timedelta(days=12)).isoformat()}).get_json()
    client.post(f"/api/bookings/{cancelled['id']}/cancel")

    confirmed = client.get("/api/bookings", query_string={"status": "confirmed"}).get_json()
    assert confirmed["count"] == 1

    none_status = client.get("/api/bookings", query_string={"status": "cancelled"}).get_json()
    assert none_status["count"] == 1

    window = client.get("/api/bookings", query_string={
        "date_from": base.isoformat(), "date_to": (base + timedelta(days=5)).isoformat()}).get_json()
    assert window["count"] == 1


def test_service_layer_overlap_conflict(services) -> None:
    """Проверка бизнес-правила на уровне сервисов без HTTP."""
    room = services["rooms"].create({"number": "500", "room_type": "Стандарт", "capacity": 2,
                                     "price_per_night": 1000.0, "floor": 5})
    guest = services["guests"].create({"full_name": "Прямой Тест", "email": "direct@example.com"})
    start = date(2030, 1, 1)
    services["bookings"].create({"room_id": room.id, "guest_id": guest.id,
                                 "check_in": start.isoformat(),
                                 "check_out": date(2030, 1, 5).isoformat()})
    with pytest.raises(BookingConflictError) as exc_info:
        services["bookings"].create({"room_id": room.id, "guest_id": guest.id,
                                     "check_in": date(2030, 1, 3).isoformat(),
                                     "check_out": date(2030, 1, 8).isoformat()})
    assert exc_info.value.status_code == 409

    with pytest.raises(ValidationError):
        services["rooms"].create({"number": "", "room_type": "Стандарт"})
