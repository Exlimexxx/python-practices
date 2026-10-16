"""Тесты ORM-моделей: поля, связи, ограничения целостности."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.booking import Booking, BookingStatus
from app.models.guest import Guest
from app.models.room import Room


def test_guest_fields(session: Session) -> None:
    guest = Guest(full_name="Иванов Иван", email="ivan@example.com", phone="+79001112233")
    session.add(guest)
    session.commit()
    assert guest.id is not None
    assert guest.full_name == "Иванов Иван"
    assert guest.bookings == []


def test_guest_email_is_unique(session: Session) -> None:
    session.add(Guest(full_name="A", email="dup@example.com", phone="1"))
    session.commit()
    session.add(Guest(full_name="B", email="dup@example.com", phone="2"))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_room_fields_and_defaults(session: Session) -> None:
    room = Room(number="101", room_type="Стандарт", capacity=2, price_per_night=Decimal("3000.00"))
    session.add(room)
    session.commit()
    assert room.id is not None
    assert room.is_active is True
    assert room.price_per_night == Decimal("3000.00")


def test_room_number_is_unique(session: Session) -> None:
    session.add(Room(number="5", room_type="A", capacity=1, price_per_night=Decimal("1")))
    session.commit()
    session.add(Room(number="5", room_type="B", capacity=1, price_per_night=Decimal("2")))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_booking_relationships(session: Session) -> None:
    guest = Guest(full_name="Петров Пётр", email="petr@example.com", phone="+79002223344")
    room = Room(number="202", room_type="Люкс", capacity=4, price_per_night=Decimal("7000.00"))
    session.add_all([guest, room])
    session.commit()

    booking = Booking(
        guest_id=guest.id,
        room_id=room.id,
        check_in=date(2025, 6, 1),
        check_out=date(2025, 6, 4),
        status=BookingStatus.ACTIVE.value,
        total_price=Decimal("21000.00"),
    )
    session.add(booking)
    session.commit()

    session.refresh(guest)
    session.refresh(room)
    assert booking in guest.bookings
    assert booking in room.bookings
    assert booking.guest.email == "petr@example.com"
    assert booking.room.number == "202"
    assert booking.nights == 3


def test_booking_check_constraint_dates(session: Session) -> None:
    guest = Guest(full_name="X", email="x@example.com", phone="0")
    room = Room(number="1", room_type="A", capacity=1, price_per_night=Decimal("100"))
    session.add_all([guest, room])
    session.commit()

    session.add(
        Booking(
            guest_id=guest.id,
            room_id=room.id,
            check_in=date(2025, 6, 5),
            check_out=date(2025, 6, 1),
            total_price=Decimal("100"),
        )
    )
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_foreign_key_violation(session: Session) -> None:
    session.add(
        Booking(
            guest_id=999,
            room_id=999,
            check_in=date(2025, 6, 1),
            check_out=date(2025, 6, 2),
            total_price=Decimal("100"),
        )
    )
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()
