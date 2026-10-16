"""Тесты аналитического маршрута."""
from __future__ import annotations

from tests.helpers import payment_payload


def test_summary_requires_authentication(client):
    response = client.get("/reports/summary")
    assert response.status_code == 401


def test_summary_is_forbidden_for_guest(client, guest):
    response = client.get("/reports/summary", headers=guest["headers"])
    assert response.status_code == 403
    assert response.json()["error"] == "PERMISSION_DENIED"


def test_summary_aggregates_all_entities(client, admin, guest, room, booking):
    client.post(
        "/payments",
        json=payment_payload(booking["id"], booking["price_total"]),
        headers=guest["headers"],
    )
    response = client.get("/reports/summary", headers=admin["headers"])
    assert response.status_code == 200
    body = response.json()

    assert body["total_rooms"] == 1
    assert body["available_rooms"] == 1
    assert body["total_users"] >= 2
    assert body["confirmed_bookings"] == 1
    assert body["total_bookings"] == 1
    assert body["total_payments"] == 1
    assert body["revenue_total"] == booking["price_total"]
    assert body["refunded_total"] == 0.0
    assert body["average_nights"] == float(booking["nights"])
    assert body["most_popular_room_type"] == "standard"


def test_summary_reacts_to_cancellations(client, admin, guest, room, booking):
    client.post(f"/bookings/{booking['id']}/cancel", headers=guest["headers"])
    body = client.get("/reports/summary", headers=admin["headers"]).json()
    assert body["cancelled_bookings"] == 1
    assert body["confirmed_bookings"] == 0
    assert body["revenue_total"] == 0.0
