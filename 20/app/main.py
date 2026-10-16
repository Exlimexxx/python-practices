"""Сервис бронирования гостиницы: REST API, health check, логирование и персистентность."""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from datetime import date
from typing import Iterator

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field, EmailStr, model_validator
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.models import Base, Booking

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("hotel.booking")


class BookingCreate(BaseModel):
    room_id: int = Field(gt=0)
    guest_id: int = Field(gt=0)
    guest_name: str = Field(min_length=2, max_length=120)
    guest_email: EmailStr
    check_in: date
    check_out: date
    price_per_night: float = Field(ge=0)

    @model_validator(mode="after")
    def validate_dates(self):
        if self.check_out <= self.check_in:
            raise ValueError("Дата выезда должна быть позже даты заезда")
        return self


class BookingUpdate(BaseModel):
    status: str = Field(pattern="^(confirmed|cancelled)$")


def create_app(database_url: str | None = None) -> FastAPI:
    url = database_url or os.getenv(
        "DATABASE_URL", "sqlite:///./hotel_bookings.db"
    )
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    engine = create_engine(url, connect_args=connect_args, pool_pre_ping=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        yield
        engine.dispose()

    app = FastAPI(title="Hotel Booking Service", version="1.0.0", lifespan=lifespan)
    app.state.engine = engine
    app.state.SessionLocal = SessionLocal

    def get_db() -> Iterator[Session]:
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    @app.get("/health")
    def health(db: Session = Depends(get_db)):
        # Простая проверка подтверждает доступность и приложения, и базы данных.
        db.execute(select(1))
        return {"status": "healthy", "service": "booking"}

    @app.get("/bookings")
    def list_bookings(db: Session = Depends(get_db)):
        items = db.scalars(select(Booking).order_by(Booking.id)).all()
        return [serialize(item) for item in items]

    @app.get("/bookings/{booking_id}")
    def get_booking(booking_id: int, db: Session = Depends(get_db)):
        item = db.get(Booking, booking_id)
        if item is None:
            raise HTTPException(404, "Бронирование не найдено")
        return serialize(item)

    @app.post("/bookings", status_code=201)
    def create_booking(payload: BookingCreate, db: Session = Depends(get_db)):
        overlap = db.scalar(
            select(Booking).where(
                Booking.room_id == payload.room_id,
                Booking.status == "confirmed",
                Booking.check_in < payload.check_out,
                Booking.check_out > payload.check_in,
            ).limit(1)
        )
        if overlap is not None:
            raise HTTPException(409, "Период пересекается с существующим бронированием")
        nights = (payload.check_out - payload.check_in).days
        item = Booking(
            room_id=payload.room_id,
            guest_id=payload.guest_id,
            guest_name=payload.guest_name.strip(),
            guest_email=str(payload.guest_email),
            check_in=payload.check_in,
            check_out=payload.check_out,
            status="confirmed",
            price_total=round(payload.price_per_night * nights, 2),
        )
        db.add(item)
        try:
            db.commit()
            db.refresh(item)
        except IntegrityError as exc:
            db.rollback()
            logger.exception("Не удалось сохранить бронирование")
            raise HTTPException(409, "Конфликт данных бронирования") from exc
        logger.info("Создано бронирование id=%s room_id=%s", item.id, item.room_id)
        return serialize(item)

    @app.patch("/bookings/{booking_id}")
    def update_booking(booking_id: int, payload: BookingUpdate, db: Session = Depends(get_db)):
        item = db.get(Booking, booking_id)
        if item is None:
            raise HTTPException(404, "Бронирование не найдено")
        item.status = payload.status
        db.commit()
        db.refresh(item)
        logger.info("Изменён статус бронирования id=%s status=%s", item.id, item.status)
        return serialize(item)

    @app.delete("/bookings/{booking_id}", status_code=204)
    def delete_booking(booking_id: int, db: Session = Depends(get_db)):
        item = db.get(Booking, booking_id)
        if item is None:
            raise HTTPException(404, "Бронирование не найдено")
        db.delete(item)
        db.commit()
        logger.info("Удалено бронирование id=%s", booking_id)
        return None

    return app


def serialize(item: Booking) -> dict:
    return {
        "id": item.id,
        "room_id": item.room_id,
        "guest_id": item.guest_id,
        "guest_name": item.guest_name,
        "guest_email": item.guest_email,
        "check_in": item.check_in.isoformat(),
        "check_out": item.check_out.isoformat(),
        "status": item.status,
        "price_total": item.price_total,
    }


app = create_app()
