"""Тесты маршрутов номерного фонда."""
from __future__ import annotations

from datetime import date

import pytest

from tests.helpers import future_period, make_room, period_payload, room_payload


def test_admin_creates_room(client, admin):
    response = client.post("/rooms", json=room_payload("201", floor=2), headers=admin["headers"])
    assert response.status_code == 201
    body = response.json()
    assert body["number"] == "201"
    assert body["room_type"] == "standard"
    assert body["status"] == "available"


def test_create_room_requires_admin_role(client, guest):
    response = client.post("/rooms", json=room_payload("202"), headers=guest["headers"])
    assert response.status_code == 403
    assert response.json()["error"] == "PERMISSION_DENIED"


def test_create_room_requires_authentication(client):
    response = client.post("/rooms", json=room_payload("203"))
    assert response.status_code == 401


@pytest.mark.parametrize(
    "overrides",
    [
        {"capacity": 0},
        {"price_per_night": 0},
        {"price_per_night": -100},
        {"number": ""},
        {"number": "101 202"},
        {"floor": 0},
    ],
)
def test_create_room_validates_payload(client, admin, overrides):
    response = client.post(
        "/rooms", json=room_payload(**overrides), headers=admin["headers"]
    )
    assert response.status_code == 422
    assert response.json()["error"] == "VALIDATION_ERROR"


def test_duplicate_room_number_conflict(client, admin, room):
    response = client.post("/rooms", json=room_payload(room["number"]), headers=admin["headers"])
    assert response.status_code == 409
    assert response.json()["error"] == "ROOM_NUMBER_ALREADY_USED"


def test_unknown_room_returns_404(client):
    response = client.get("/rooms/4242")
    assert response.status_code == 404
    assert response.json()["error"] == "ROOM_NOT_FOUND"


def test_update_room_changes_price_and_type(client, admin, room):
    response = client.patch(
        f"/rooms/{room['id']}",
        json={"price_per_night": 7800.5, "room_type": "lux", "description": "С видом на море"},
        headers=admin["headers"],
    )
    assert response.status_code == 200
    body = response.json()
    assert body["price_per_night"] == 7800.5
    assert body["room_type"] == "lux"
    assert body["description"] == "С видом на море"


def test_update_room_without_changes_returns_422(client, admin, room):
    response = client.patch(f"/rooms/{room['id']}", json={}, headers=admin["headers"])
    assert response.status_code == 422
    assert response.json()["error"] == "VALIDATION_ERROR"


def test_change_room_status_blocks_booking(client, admin, guest, room):
    updated = client.put(
        f"/rooms/{room['id']}/status",
        json={"status": "maintenance"},
        headers=admin["headers"],
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "maintenance"

    check_in, check_out = future_period()
    booking = client.post(
        "/bookings",
        json={"room_id": room["id"], **period_payload(check_in, check_out)},
        headers=guest["headers"],
    )
    assert booking.status_code == 409
    assert booking.json()["error"] == "ROOM_NOT_AVAILABLE"


def test_delete_room_removes_it(client, admin, room):
    response = client.delete(f"/rooms/{room['id']}", headers=admin["headers"])
    assert response.status_code == 204
    assert client.get(f"/rooms/{room['id']}").status_code == 404


def test_delete_room_with_active_booking_conflict(client, admin, room, booking):
    response = client.delete(f"/rooms/{room['id']}", headers=admin["headers"])
    assert response.status_code == 409
    assert response.json()["error"] == "ROOM_HAS_BOOKINGS"


def test_rooms_catalog_filters_and_sorts(client, admin):
    make_room(client, admin["headers"], "301", room_type="standard", price_per_night=3000, capacity=2)
    make_room(client, admin["headers"], "302", room_type="lux", price_per_night=15000, capacity=4)
    make_room(client, admin["headers"], "303", room_type="lux", price_per_night=9000, capacity=2)

    lux = client.get("/rooms", params={"room_type": "lux"})
    assert lux.status_code == 200
    assert {item["number"] for item in lux.json()["items"]} == {"302", "303"}

    cheap = client.get("/rooms", params={"max_price": 3500})
    assert [item["number"] for item in cheap.json()["items"]] == ["301"]

    spacious = client.get("/rooms", params={"min_capacity": 4})
    assert [item["number"] for item in spacious.json()["items"]] == ["302"]

    descending = client.get("/rooms", params={"room_type": "lux", "sort": "price_desc"})
    prices = [item["price_per_night"] for item in descending.json()["items"]]
    assert prices == sorted(prices, reverse=True)


def test_rooms_catalog_validates_filter_range(client):
    response = client.get("/rooms", params={"min_price": 9000, "max_price": 1000})
    assert response.status_code == 422
    assert response.json()["error"] == "VALIDATION_ERROR"


def test_rooms_catalog_is_paginated(client, admin):
    for number in ("401", "402", "403"):
        make_room(client, admin["headers"], number)

    first_page = client.get("/rooms", params={"limit": 2, "offset": 0})
    body = first_page.json()
    assert body["limit"] == 2
    assert body["total"] == 3
    assert len(body["items"]) == 2

    second_page = client.get("/rooms", params={"limit": 2, "offset": 2}).json()
    assert len(second_page["items"]) == 1


def test_available_rooms_excludes_booked_period(client, admin, room, booking):
    same_period = client.get(
        "/rooms/available",
        params=period_payload(
            date.fromisoformat(booking["check_in"]), date.fromisoformat(booking["check_out"])
        ),
    )
    assert same_period.status_code == 200
    assert room["id"] not in {item["id"] for item in same_period.json()}

    later_in, later_out = future_period(offset_days=60, nights=2)
    later = client.get("/rooms/available", params=period_payload(later_in, later_out))
    assert room["id"] in {item["id"] for item in later.json()}


def test_available_rooms_rejects_inverted_period(client):
    check_in, check_out = future_period()
    response = client.get(
        "/rooms/available", params=period_payload(check_out, check_in)
    )
    assert response.status_code == 422
