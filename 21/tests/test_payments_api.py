"""Тесты платежей и возвратов."""
from __future__ import annotations

import pytest

from tests.helpers import payment_payload


def test_full_payment_closes_booking(client, guest, booking):
    response = client.post(
        "/payments",
        json=payment_payload(booking["id"], booking["price_total"], method="transfer"),
        headers=guest["headers"],
    )
    assert response.status_code == 201
    assert response.json()["status"] == "paid"

    refreshed = client.get(f"/bookings/{booking['id']}", headers=guest["headers"]).json()
    assert refreshed["paid_total"] == booking["price_total"]
    assert refreshed["remaining_amount"] == 0.0


def test_partial_payments_track_remaining_amount(client, guest, booking):
    first = client.post(
        "/payments", json=payment_payload(booking["id"], 5000), headers=guest["headers"]
    )
    assert first.status_code == 201

    after_first = client.get(f"/bookings/{booking['id']}", headers=guest["headers"]).json()
    assert after_first["paid_total"] == 5000
    assert after_first["remaining_amount"] == booking["price_total"] - 5000

    second = client.post(
        "/payments",
        json=payment_payload(booking["id"], 1000, method="cash"),
        headers=guest["headers"],
    )
    assert second.status_code == 201

    payments = client.get(
        f"/bookings/{booking['id']}/payments", headers=guest["headers"]
    ).json()
    assert [item["amount"] for item in payments] == [5000.0, 1000.0]


def test_overpayment_is_rejected(client, guest, booking):
    response = client.post(
        "/payments",
        json=payment_payload(booking["id"], booking["price_total"] + 100),
        headers=guest["headers"],
    )
    assert response.status_code == 409
    body = response.json()
    assert body["error"] == "PAYMENT_AMOUNT_EXCEEDED"
    assert body["details"]["remaining_amount"] == booking["price_total"]


def test_payment_after_full_payment_is_rejected(client, guest, booking):
    client.post(
        "/payments",
        json=payment_payload(booking["id"], booking["price_total"]),
        headers=guest["headers"],
    )
    response = client.post(
        "/payments", json=payment_payload(booking["id"], 1), headers=guest["headers"]
    )
    assert response.status_code == 409
    assert response.json()["error"] == "PAYMENT_AMOUNT_EXCEEDED"


@pytest.mark.parametrize("amount", [0, -500])
def test_payment_amount_must_be_positive(client, guest, booking, amount):
    response = client.post(
        "/payments", json=payment_payload(booking["id"], amount), headers=guest["headers"]
    )
    assert response.status_code == 422
    assert response.json()["error"] == "VALIDATION_ERROR"


def test_payment_for_cancelled_booking_is_rejected(client, guest, booking):
    client.post(f"/bookings/{booking['id']}/cancel", headers=guest["headers"])
    response = client.post(
        "/payments", json=payment_payload(booking["id"], 1000), headers=guest["headers"]
    )
    assert response.status_code == 409
    assert response.json()["error"] == "BOOKING_STATUS_INVALID"


def test_payment_requires_authentication(client, booking):
    response = client.post(
        "/payments", json=payment_payload(booking["id"], 1000)
    )
    assert response.status_code == 401


def test_payment_for_foreign_booking_is_forbidden(client, second_guest, booking):
    response = client.post(
        "/payments",
        json=payment_payload(booking["id"], 1000),
        headers=second_guest["headers"],
    )
    assert response.status_code == 403


def test_payment_for_unknown_booking_returns_404(client, guest):
    response = client.post(
        "/payments", json=payment_payload(999, 1000), headers=guest["headers"]
    )
    assert response.status_code == 404
    assert response.json()["error"] == "BOOKING_NOT_FOUND"


def test_refund_restores_remaining_amount_and_allows_cancellation(client, admin, guest, booking):
    payment = client.post(
        "/payments",
        json=payment_payload(booking["id"], booking["price_total"]),
        headers=guest["headers"],
    )
    assert payment.status_code == 201

    refunded = client.post(
        f"/payments/{payment.json()['id']}/refund", headers=admin["headers"]
    )
    assert refunded.status_code == 200
    assert refunded.json()["status"] == "refunded"

    refreshed = client.get(f"/bookings/{booking['id']}", headers=guest["headers"]).json()
    assert refreshed["paid_total"] == 0.0
    assert refreshed["remaining_amount"] == booking["price_total"]

    cancelled = client.post(f"/bookings/{booking['id']}/cancel", headers=guest["headers"])
    assert cancelled.status_code == 200


def test_refund_requires_admin_role(client, guest, booking):
    payment = client.post(
        "/payments", json=payment_payload(booking["id"], 1000), headers=guest["headers"]
    )
    response = client.post(
        f"/payments/{payment.json()['id']}/refund", headers=guest["headers"]
    )
    assert response.status_code == 403


def test_repeated_refund_returns_conflict(client, admin, guest, booking):
    payment = client.post(
        "/payments", json=payment_payload(booking["id"], 1000), headers=guest["headers"]
    )
    client.post(f"/payments/{payment.json()['id']}/refund", headers=admin["headers"])
    response = client.post(
        f"/payments/{payment.json()['id']}/refund", headers=admin["headers"]
    )
    assert response.status_code == 409


def test_admin_can_list_all_payments(client, admin, guest, booking):
    client.post(
        "/payments", json=payment_payload(booking["id"], 1000), headers=guest["headers"]
    )
    response = client.get("/payments", headers=admin["headers"])
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["booking_id"] == booking["id"]


def test_guest_cannot_list_all_payments(client, guest):
    response = client.get("/payments", headers=guest["headers"])
    assert response.status_code == 403


def test_unknown_payment_refund_returns_404(client, admin):
    response = client.post("/payments/4242/refund", headers=admin["headers"])
    assert response.status_code == 404
    assert response.json()["error"] == "PAYMENT_NOT_FOUND"
