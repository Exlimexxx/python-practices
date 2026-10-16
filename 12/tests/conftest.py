"""Общие фикстуры для тестов: изолированная БД в памяти на каждый тест."""
from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.database import configure_database, drop_db, get_session_factory, init_db
from app.models.room import Room
from app.services.hotel_service import HotelService


@pytest.fixture()
def session() -> Iterator[Session]:
    """Свежая база SQLite в памяти для каждого теста."""
    configure_database("sqlite+pysqlite:///:memory:")
    init_db()
    db = get_session_factory()()
    try:
        yield db
    finally:
        db.close()
        drop_db()


@pytest.fixture()
def service(session: Session) -> HotelService:
    """Сервис отеля, работающий с тестовой сессией."""
    return HotelService(session)


@pytest.fixture()
def sample_room(session: Session) -> Room:
    """Тестовый номер на 2 места."""
    room = Room(
        number="101",
        room_type="Стандарт",
        capacity=2,
        price_per_night=Decimal("3000.00"),
        is_active=True,
    )
    session.add(room)
    session.commit()
    return room


@pytest.fixture()
def booking_dates() -> tuple[date, date]:
    """Стандартный интервал дат для тестов."""
    return date(2025, 6, 1), date(2025, 6, 5)
