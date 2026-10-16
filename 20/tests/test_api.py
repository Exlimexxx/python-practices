from fastapi.testclient import TestClient
import pytest
from app.main import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(f"sqlite:///{tmp_path / 'test_hotel.db'}")
    with TestClient(app) as test_client:
        yield test_client


def payload(**overrides):
    data = {
        "room_id": 12, "guest_id": 8, "guest_name": "Анна Иванова",
        "guest_email": "anna@example.com", "check_in": "2026-11-01",
        "check_out": "2026-11-05", "price_per_night": 4200,
    }
    data.update(overrides)
    return data


def test_health_checks_database(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "booking"}


def test_create_booking_calculates_total(client):
    response = client.post("/bookings", json=payload())
    assert response.status_code == 201
    assert response.json()["price_total"] == 16800
    assert response.json()["status"] == "confirmed"


def test_list_bookings(client):
    client.post("/bookings", json=payload())
    assert len(client.get("/bookings").json()) == 1


def test_get_booking(client):
    item = client.post("/bookings", json=payload()).json()
    assert client.get(f"/bookings/{item['id']}").json()["guest_name"] == "Анна Иванова"


def test_missing_booking_is_404(client):
    assert client.get("/bookings/999").status_code == 404


def test_delete_booking(client):
    item = client.post("/bookings", json=payload()).json()
    assert client.delete(f"/bookings/{item['id']}").status_code == 204
    assert client.get(f"/bookings/{item['id']}").status_code == 404


def test_overlap_is_conflict(client):
    assert client.post("/bookings", json=payload()).status_code == 201
    second = client.post("/bookings", json=payload(guest_id=9, check_in="2026-11-04", check_out="2026-11-07"))
    assert second.status_code == 409


def test_adjacent_stays_are_allowed(client):
    client.post("/bookings", json=payload())
    next_stay = client.post("/bookings", json=payload(guest_id=9, check_in="2026-11-05", check_out="2026-11-07"))
    assert next_stay.status_code == 201


def test_invalid_dates_are_rejected(client):
    response = client.post("/bookings", json=payload(check_in="2026-11-06", check_out="2026-11-05"))
    assert response.status_code == 422


def test_negative_price_is_rejected(client):
    assert client.post("/bookings", json=payload(price_per_night=-1)).status_code == 422


def test_cancelled_booking_does_not_block_room(client):
    first = client.post("/bookings", json=payload()).json()
    client.patch(f"/bookings/{first['id']}", json={"status":"cancelled"})
    second = client.post("/bookings", json=payload(guest_id=9, check_in="2026-11-02", check_out="2026-11-04"))
    assert second.status_code == 201
