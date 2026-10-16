"""Наполнение базы демонстрационными данными (идемпотентно)."""
from __future__ import annotations

import logging
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Booking, Guest, Room

logger = logging.getLogger(__name__)

ROOM_SAMPLES: list[dict[str, object]] = [
    {"number": "101", "room_type": "Стандарт", "capacity": 2, "price_per_night": 4200.0,
     "floor": 1, "description": "Стандартный двухместный номер с видом во двор.", "is_active": True},
    {"number": "102", "room_type": "Стандарт", "capacity": 1, "price_per_night": 3100.0,
     "floor": 1, "description": "Одноместный номер для командировок.", "is_active": True},
    {"number": "203", "room_type": "Комфорт", "capacity": 3, "price_per_night": 6800.0,
     "floor": 2, "description": "Просторный номер с балконом и кондиционером.", "is_active": True},
    {"number": "305", "room_type": "Люкс", "capacity": 4, "price_per_night": 12500.0,
     "floor": 3, "description": "Люкс с гостиной зоной и панорамным окном.", "is_active": True},
    {"number": "401", "room_type": "Апартаменты", "capacity": 5, "price_per_night": 18000.0,
     "floor": 4, "description": "Двухкомнатные апартаменты с кухней.", "is_active": True},
    {"number": "402", "room_type": "Стандарт", "capacity": 2, "price_per_night": 4000.0,
     "floor": 4, "description": "Номер закрыт на ремонт.", "is_active": False},
]

GUEST_SAMPLES: list[dict[str, str]] = [
    {"full_name": "Иванов Иван Иванович", "email": "ivanov@example.com", "phone": "+7-900-111-22-33",
     "passport": "4501 123456", "city": "Москва"},
    {"full_name": "Петрова Анна Сергеевна", "email": "petrova@example.com", "phone": "+7-900-222-33-44",
     "passport": "4502 654321", "city": "Санкт-Петербург"},
    {"full_name": "Сидоров Пётр Алексеевич", "email": "sidorov@example.com", "phone": "+7-900-333-44-55",
     "passport": "4503 111222", "city": "Казань"},
]


def seed_database(session: Session) -> dict[str, int]:
    """Добавляет образцы данных, если таблицы пусты. Возвращает счётчики."""
    counters = {"rooms": 0, "guests": 0, "bookings": 0}

    if (session.scalar(select(func.count(Room.id))) or 0) == 0:
        rooms = [Room(**sample) for sample in ROOM_SAMPLES]
        session.add_all(rooms)
        session.flush()
        counters["rooms"] = len(rooms)
        logger.info("Создано номеров: %s", len(rooms))
    else:
        rooms = list(session.scalars(select(Room).order_by(Room.number)))

    if (session.scalar(select(func.count(Guest.id))) or 0) == 0:
        guests = [Guest(**sample) for sample in GUEST_SAMPLES]
        session.add_all(guests)
        session.flush()
        counters["guests"] = len(guests)
        logger.info("Создано гостей: %s", len(guests))
    else:
        guests = list(session.scalars(select(Guest).order_by(Guest.id)))

    if (session.scalar(select(func.count(Booking.id))) or 0) == 0 and rooms and guests:
        today = date.today()
        samples = [
            Booking(room=rooms[0], guest=guests[0], check_in=today + timedelta(days=1),
                    check_out=today + timedelta(days=4), guests_count=2, status="confirmed",
                    total_price=rooms[0].price_per_night * 3,
                    comment="Заезд после 14:00"),
            Booking(room=rooms[2], guest=guests[1], check_in=today + timedelta(days=10),
                    check_out=today + timedelta(days=13), guests_count=2, status="confirmed",
                    total_price=rooms[2].price_per_night * 3, comment=""),
            Booking(room=rooms[3], guest=guests[2], check_in=today - timedelta(days=20),
                    check_out=today - timedelta(days=17), guests_count=2, status="cancelled",
                    total_price=rooms[3].price_per_night * 3, comment="Отменено гостем"),
        ]
        session.add_all(samples)
        counters["bookings"] = len(samples)
        logger.info("Создано бронирований: %s", len(samples))

    session.commit()
    return counters
