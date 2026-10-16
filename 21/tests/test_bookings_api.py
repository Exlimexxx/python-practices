"""Тесты бронирований: бизнес-правила, права доступа, проверки периода."""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from tests.helpers import booking_payload, future_period, payment_payload, room_payload


def test_create_booking_calculates_price(client, guest, room):
    check_in, check_out = future_period(offset_days=5, nights=4)
    response = client.post(
        "/bookings",
        json=booking_payload(room["id"], check_in, check_out, comment="Поздний заезд"),
        headers=guest["headers"],
    )
    assert response.status_code == 201
    body = response.json()
    assert body["nights"] == 4
    assert body["price_total"] == 4 * room["price_per_night"]
    assert body["remaining_amount"] == body["price_total"]
    assert body["paid_total"] == 0.0
    assert body["status"] == "confirmed"
    assert body["room_number"] == room["number"]
    assert body["user_email"] == guest["email"]


def test_create_booking_for_unknown_room_returns_404(client, guest):
    check_in, check_out = future_period()
    response = client.post(
        "/bookings",
        json=booking_payload(9999, check_in, check_out),
        headers=guest["headers"],
    )
    assert response.status_code == 404
    assert response.json()["error"] == "ROOM_NOT_FOUND"


def test_create_booking_requires_authentication(client, room):
    check_in, check_out = future_period()
    response = client.post("/bookings", json=booking_payload(room["id"], check_in, check_out))
    assert response.status_code == 401
    assert response.json()["error"] == "AUTHENTICATION_FAILED"


@pytest.mark.parametrize(
    "offset_in,offset_out",
    [(5, 5), (8, 5), (5, 5 + 400)],
)
def test_create_booking_validates_period(client, guest, room, offset_in, offset_out):
    response = client.post(
        "/bookings",
        json=booking_payload(room["id"], _day(offset_in), _day(offset_out)),
        headers=guest["headers"],
    )
    assert response.status_code == 422
    assert response.json()["error"] == "VALIDATION_ERROR"


def test_create_booking_rejects_past_check_in(client, guest, room):
    check_in, check_out = _day(-3), _day(1)
    response = client.post(
        "/bookings",
        json=booking_payload(room["id"], check_in, check_out),
        headers=guest["headers"],
    )
    assert response.status_code == 422
    assert response.json()["error"] == "VALIDATION_ERROR"


@pytest.mark.parametrize("shift_days", [0, 1, 3])
def test_overlapping_booking_is_rejected(client, second_guest, room, booking, shift_days):
    check_in = date.fromisoformat(booking["check_in"]) + timedelta(days=shift_days)
    check_out = date.fromisoformat(booking["check_out"]) + timedelta(days=shift_days)
    response = client.post(
        "/bookings",
        json=booking_payload(room["id"], check_in, check_out),
        headers=second_guest["headers"],
    )
    assert response.status_code == 409
    body = response.json()
    assert body["error"] == "BOOKING_OVERLAP"
    assert body["details"]["conflicting_booking_id"] == booking["id"]


def test_adjacent_period_is_allowed(client, second_guest, room, booking):
    check_in = date.fromisoformat(booking["check_out"])
    check_out = check_in + timedelta(days=2)
    response = client.post(
        "/bookings",
        json=booking_payload(room["id"], check_in, check_out),
        headers=second_guest["headers"],
    )
    assert response.status_code == 201


def test_cancelled_booking_frees_the_period(client, guest, second_guest, room, booking):
    cancelled = client.post(f"/bookings/{booking['id']}/cancel", headers=guest["headers"])
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"

    response = client.post(
        "/bookings",
        json=booking_payload(
            room["id"],
            date.fromisoformat(booking["check_in"]),
            date.fromisoformat(booking["check_out"]),
        ),
        headers=second_guest["headers"],
    )
    assert response.status_code == 201


def test_cancel_foreign_booking_is_forbidden(client, second_guest, booking):
    response = client.post(f"/bookings/{booking['id']}/cancel", headers=second_guest["headers"])
    assert response.status_code == 403
    assert response.json()["error"] == "PERMISSION_DENIED"


def test_paid_booking_cannot_be_cancelled(client, guest, booking):
    paid = client.post(
        "/payments", json=payment_payload(booking["id"], 1000), headers=guest["headers"]
    )
    assert paid.status_code == 201

    response = client.post(f"/bookings/{booking['id']}/cancel", headers=guest["headers"])
    assert response.status_code == 409
    assert response.json()["error"] == "BOOKING_STATUS_INVALID"


def test_completed_booking_cannot_be_cancelled(client, admin, guest, booking):
    client.post(
        "/payments",
        json=payment_payload(booking["id"], booking["price_total"]),
        headers=guest["headers"],
    )
    completed = client.post(f"/bookings/{booking['id']}/complete", headers=admin["headers"])
    assert completed.status_code == 200

    response = client.post(f"/bookings/{booking['id']}/cancel", headers=guest["headers"])
    assert response.status_code == 409


def test_guest_sees_only_own_bookings(client, guest, second_guest, room, booking):
    own = client.get("/bookings", headers=guest["headers"])
    assert own.status_code == 200
    assert [item["id"] for item in own.json()["items"]] == [booking["id"]]

    foreign = client.get("/bookings", headers=second_guest["headers"])
    assert foreign.json()["total"] == 0
    assert foreign.json()["items"] == []


def test_admin_sees_all_bookings_and_filters_by_status(client, admin, guest, room, booking):
    all_bookings = client.get("/bookings", headers=admin["headers"])
    assert all_bookings.status_code == 200
    assert booking["id"] in {item["id"] for item in all_bookings.json()["items"]}

    confirmed = client.get(
        "/bookings", params={"status": "confirmed"}, headers=admin["headers"]
    )
    assert booking["id"] in {item["id"] for item in confirmed.json()["items"]}

    cancelled = client.get("/bookings", params={"status": "cancelled"}, headers=admin["headers"])
    assert booking["id"] not in {item["id"] for item in cancelled.json()["items"]}

    by_room = client.get("/bookings", params={"room_id": room["id"]}, headers=admin["headers"])
    assert by_room.json()["total"] >= 1


def test_bookings_sorting_by_price(client, admin, guest, room):
    check_in, check_out = future_period(offset_days=40, nights=1)
    short = client.post(
        "/bookings",
        json=booking_payload(room["id"], check_in, check_out),
        headers=guest["headers"],
    )
    assert short.status_code == 201

    sorted_page = client.get(
        "/bookings", params={"sort": "price_desc"}, headers=admin["headers"]
    )
    prices = [item["price_total"] for item in sorted_page.json()["items"]]
    assert prices == sorted(prices, reverse=True)


def test_get_foreign_booking_is_forbidden(client, second_guest, booking):
    response = client.get(f"/bookings/{booking['id']}", headers=second_guest["headers"])
    assert response.status_code == 403


def test_get_unknown_booking_returns_404(client, guest):
    response = client.get("/bookings/777", headers=guest["headers"])
    assert response.status_code == 404
    assert response.json()["error"] == "BOOKING_NOT_FOUND"


def test_complete_requires_full_payment(client, admin, booking):
    response = client.post(f"/bookings/{booking['id']}/complete", headers=admin["headers"])
    assert response.status_code == 409
    assert response.json()["error"] == "BOOKING_NOT_PAID"
    assert response.json()["details"]["remaining_amount"] == booking["price_total"]


def test_complete_marks_booking_as_completed(client, admin, guest, booking):
    client.post(
        "/payments",
        json=payment_payload(booking["id"], booking["price_total"]),
        headers=guest["headers"],
    )
    response = client.post(f"/bookings/{booking['id']}/complete", headers=admin["headers"])
    assert response.status_code == 200
    assert response.json()["status"] == "completed"


def test_complete_is_forbidden_for_guest(client, guest, booking):
    response = client.post(f"/bookings/{booking['id']}/complete", headers=guest["headers"])
    assert response.status_code == 403


def test_create_booking_on_unavailable_room_returns_conflict(client, admin, guest):
    created = client.post(
        "/rooms",
        json=room_payload("505", status="maintenance"),
        headers=admin["headers"],
    )
    assert created.status_code == 201

    check_in, check_out = future_period()
    response = client.post(
        "/bookings",
        json=booking_payload(created.json()["id"], check_in, check_out),
        headers=guest["headers"],
    )
    assert response.status_code == 409
    assert response.json()["error"] == "ROOM_NOT_AVAILABLE"


def _day(offset_days: int) -> date:
    return date.today() + timedelta(days=offset_days)
