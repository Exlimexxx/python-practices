import asyncio
import time
from fastapi.testclient import TestClient
import pytest
from app.rooms_service import create_app as create_rooms_app
from app.guests_service import create_app as create_guests_app
from app.bookings_service import create_app as create_bookings_app
from app.resilience import CircuitBreaker, CircuitOpenError, retry_async
from app.storage import HotelStore
from app import bookings_service, events


def test_room_service_crud(tmp_path):
    client = TestClient(create_rooms_app(str(tmp_path / "rooms.db")))
    response = client.post("/rooms", json={"number":"101", "category":"standard", "capacity":2, "price_per_night":1200})
    assert response.status_code == 201 and response.json()["id"] == 1
    assert client.get("/rooms").json()[0]["number"] == "101"
    assert client.delete("/rooms/1").status_code == 204
    assert client.get("/rooms/1").status_code == 404


def test_guest_service_rejects_duplicate_email(tmp_path):
    client = TestClient(create_guests_app(str(tmp_path / "guests.db")))
    data = {"full_name":"Анна Иванова", "email":"anna@example.test", "phone":"+000"}
    assert client.post("/guests", json=data).status_code == 201
    assert client.post("/guests", json=data).status_code == 409


def test_service_healthchecks(tmp_path):
    assert TestClient(create_rooms_app(str(tmp_path / "r.db"))).get("/health").json()["status"] == "healthy"
    assert TestClient(create_guests_app(str(tmp_path / "g.db"))).get("/health").status_code == 200


def test_booking_store_detects_overlapping_periods(tmp_path):
    store = HotelStore("bookings", tmp_path / "b.db")
    store.create({"room_id":1,"guest_id":1,"check_in":"2026-11-01","check_out":"2026-11-05","price_total":4000})
    assert store.overlaps(1, "2026-11-04", "2026-11-06")
    assert not store.overlaps(1, "2026-11-05", "2026-11-07")
    store.close()


def test_booking_service_rejects_reversed_dates(tmp_path):
    client = TestClient(create_bookings_app(str(tmp_path / "b.db")))
    response = client.post("/bookings", json={"room_id":1,"guest_id":1,"check_in":"2026-11-05","check_out":"2026-11-01"})
    assert response.status_code == 400


def test_retry_succeeds_after_temporary_errors():
    async def scenario():
        attempts = {"n":0}
        async def operation():
            attempts["n"] += 1
            if attempts["n"] < 3:
                raise RuntimeError("temporary")
            return "ok"
        assert await retry_async(operation, attempts=3, base_delay=0) == "ok"
        assert attempts["n"] == 3
    asyncio.run(scenario())


def test_retry_raises_after_max_attempts():
    async def scenario():
        attempts = {"n":0}
        async def operation():
            attempts["n"] += 1
            raise RuntimeError("offline")
        with pytest.raises(RuntimeError, match="offline"):
            await retry_async(operation, attempts=2, base_delay=0)
        assert attempts["n"] == 2
    asyncio.run(scenario())


def test_circuit_breaker_opens_and_blocks_call():
    async def scenario():
        breaker = CircuitBreaker(failure_threshold=1, reset_timeout=10)
        async def failing(): raise RuntimeError("down")
        with pytest.raises(RuntimeError): await breaker.call(failing)
        assert breaker.state == "OPEN"
        with pytest.raises(CircuitOpenError): await breaker.call(failing)
    asyncio.run(scenario())


def test_circuit_breaker_closes_after_success():
    async def scenario():
        breaker = CircuitBreaker(failure_threshold=1, reset_timeout=0)
        async def failing(): raise RuntimeError("down")
        with pytest.raises(RuntimeError): await breaker.call(failing)
        async def success(): return 42
        assert await breaker.call(success) == 42
        assert breaker.state == "CLOSED"
    asyncio.run(scenario())


def test_event_bus_publishes_and_consumes_booking_created(monkeypatch):
    monkeypatch.delenv("RABBITMQ_URL", raising=False)
    async def scenario():
        event = {"event_type":"BookingCreated", "booking":{"id":12}}
        await events.publish_event(event)
        assert await events.receive_local_event() == event
    asyncio.run(scenario())


def test_booking_price_is_calculated_from_room_rate(tmp_path, monkeypatch):
    client = TestClient(create_bookings_app(str(tmp_path / "b.db")))
    async def fake_fetch(url, breaker):
        if "/rooms/" in url:
            return {"id":1,"active":1,"price_per_night":1500.0}
        return {"id":2,"full_name":"Тест"}
    monkeypatch.setattr(bookings_service, "fetch_remote_json", fake_fetch)
    monkeypatch.setattr(bookings_service, "publish_event", events.publish_event)
    response = client.post("/bookings", json={"room_id":1,"guest_id":2,"check_in":"2026-11-01","check_out":"2026-11-04"})
    assert response.status_code == 201
    assert response.json()["price_total"] == 4500.0
    asyncio.run(events.receive_local_event())


def test_booking_service_prevents_overlapping_reservations(tmp_path, monkeypatch):
    client = TestClient(create_bookings_app(str(tmp_path / "b.db")))
    async def fake_fetch(url, breaker):
        return {"id":1,"active":1,"price_per_night":1000} if "/rooms/" in url else {"id":1}
    monkeypatch.setattr(bookings_service, "fetch_remote_json", fake_fetch)
    payload = {"room_id":1,"guest_id":1,"check_in":"2026-12-01","check_out":"2026-12-05"}
    first = client.post("/bookings", json=payload)
    second = client.post("/bookings", json={**payload,"check_in":"2026-12-04","check_out":"2026-12-06"})
    assert first.status_code == 201
    assert second.status_code == 409
    asyncio.run(events.receive_local_event())


def test_room_validation_rejects_zero_capacity(tmp_path):
    client = TestClient(create_rooms_app(str(tmp_path / "rooms.db")))
    response = client.post("/rooms", json={"number":"0", "category":"standard", "capacity":0, "price_per_night":100})
    assert response.status_code == 422
