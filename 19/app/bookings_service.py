from __future__ import annotations
import os
import sqlite3
from datetime import date
from typing import Any
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from app.events import publish_event
from app.resilience import CircuitBreaker, CircuitOpenError, retry_async
from app.storage import HotelStore

room_breaker = CircuitBreaker(failure_threshold=2, reset_timeout=3.0)
guest_breaker = CircuitBreaker(failure_threshold=2, reset_timeout=3.0)


class BookingIn(BaseModel):
    room_id: int = Field(gt=0)
    guest_id: int = Field(gt=0)
    check_in: date
    check_out: date


async def fetch_remote_json(url: str, breaker: CircuitBreaker) -> dict[str, Any]:
    async def operation() -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=1.5) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
    return await breaker.call(lambda: retry_async(operation, attempts=3))


def create_app(db_path: str | None = None) -> FastAPI:
    app = FastAPI(title="Bookings Service", version="1.0.0")
    store = HotelStore("bookings", db_path or os.getenv("BOOKINGS_DB_PATH", "data/bookings.db"))
    app.state.store = store

    @app.get("/health")
    def health(): return {"status": "healthy", "service": "bookings"}

    @app.get("/bookings")
    def list_bookings(): return store.list()

    @app.get("/bookings/{booking_id}")
    def get_booking(booking_id: int):
        item = store.get(booking_id)
        if item is None: raise HTTPException(404, "Бронирование не найдено")
        return item

    @app.post("/bookings", status_code=201)
    async def create_booking(payload: BookingIn):
        if payload.check_in >= payload.check_out:
            raise HTTPException(400, "Дата выезда должна быть позже даты заезда")
        rooms_url = os.getenv("ROOMS_SERVICE_URL", "http://rooms-service:8001")
        guests_url = os.getenv("GUESTS_SERVICE_URL", "http://guests-service:8002")
        try:
            room = await fetch_remote_json(f"{rooms_url}/rooms/{payload.room_id}", room_breaker)
            await fetch_remote_json(f"{guests_url}/guests/{payload.guest_id}", guest_breaker)
        except CircuitOpenError as exc:
            raise HTTPException(503, "Вызов зависимого сервиса временно приостановлен Circuit Breaker") from exc
        except Exception as exc:
            raise HTTPException(503, "Не удалось проверить номер или гостя") from exc
        if not room.get("active", 1): raise HTTPException(409, "Номер недоступен")
        if store.overlaps(payload.room_id, payload.check_in.isoformat(), payload.check_out.isoformat()):
            raise HTTPException(409, "Период пересекается с существующим бронированием")
        nights = (payload.check_out - payload.check_in).days
        try:
            item = store.create({
                "room_id": payload.room_id, "guest_id": payload.guest_id,
                "check_in": payload.check_in.isoformat(), "check_out": payload.check_out.isoformat(),
                "status": "confirmed", "price_total": round(float(room["price_per_night"]) * nights, 2),
            })
        except sqlite3.IntegrityError as exc:
            raise HTTPException(409, "Конфликт данных бронирования") from exc
        await publish_event({"event_type": "BookingCreated", "booking": item})
        return item

    @app.delete("/bookings/{booking_id}", status_code=204)
    def cancel_booking(booking_id: int):
        item = store.get(booking_id)
        if item is None: raise HTTPException(404, "Бронирование не найдено")
        store.update(booking_id, {"status": "cancelled"})
        return None

    return app

app = create_app()
