"""Тесты репозиториев: CRUD, поиск, фильтрация, сортировки, пересечения."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.exceptions import DuplicateError, ValidationError
from app.models.booking import Booking, BookingStatus
from app.repositories.booking_repository import BookingRepository
from app.repositories.guest_repository import GuestRepository
from app.repositories.room_repository import RoomRepository


def test_guest_crud(session: Session) -> None:
    repo = GuestRepository(session)
    guest = repo.create("Иванов Иван", "IVAN@example.com", "+79001112233")
    session.commit()
    assert guest.email == "ivan@example.com"  # приведён к нижнему регистру
    assert repo.get_by_id(guest.id) is guest
    assert repo.get_by_email("ivan@example.com") is guest
    assert repo.count() == 1

    repo.update_guest(guest, phone="+70000000000")
    session.commit()
    assert guest.phone == "+70000000000"

    assert repo.delete_by_id(guest.id) is True
    session.commit()
    assert repo.count() == 0
    assert repo.delete_by_id(guest.id) is False


def test_guest_duplicate_email(session: Session) -> None:
    repo = GuestRepository(session)
    repo.create("A", "a@example.com", "1")
    session.commit()
    with pytest.raises(DuplicateError):
        repo.create("B", "a@example.com", "2")


def test_guest_validation(session: Session) -> None:
    repo = GuestRepository(session)
    with pytest.raises(ValidationError):
        repo.create("", "a@example.com", "1")
    with pytest.raises(ValidationError):
        repo.create("A", "not-an-email", "1")


def test_guest_search_by_several_attributes(session: Session) -> None:
    repo = GuestRepository(session)
    repo.create("Иванов Иван", "ivan@example.com", "+79001112233")
    repo.create("Иванова Анна", "anna@example.com", "+79005556677")
    session.commit()

    assert len(repo.search(full_name="Иванов")) == 2
    assert len(repo.search(full_name="Иванов", phone="555")) == 1
    assert repo.search(full_name="Иванов", phone="555")[0].full_name == "Иванова Анна"
    assert len(repo.find_by_name_or_email("anna")) == 1


def test_room_filter_and_sort(session: Session) -> None:
    repo = RoomRepository(session)
    repo.create("101", "Стандарт", 2, "3000")
    repo.create("102", "Люкс", 4, "7000")
    repo.create("103", "Эконом", 1, "1500")
    session.commit()

    assert len(repo.search(is_active=True)) == 3
    assert len(repo.search(min_capacity=3)) == 1
    assert len(repo.search(room_type="Люкс", min_price=5000)) == 1
    assert len(repo.search(min_price=2000, max_price=5000)) == 1

    by_price = repo.list_sorted_by_price()
    assert [r.number for r in by_price] == ["103", "101", "102"]
    by_capacity = repo.list_sorted_by_capacity()
    assert [r.number for r in by_capacity] == ["102", "101", "103"]


def test_room_duplicate_number(session: Session) -> None:
    repo = RoomRepository(session)
    repo.create("101", "Стандарт", 2, "3000")
    session.commit()
    with pytest.raises(DuplicateError):
        repo.create("101", "Люкс", 4, "9000")


def test_booking_overlap_detection(session: Session) -> None:
    guests = GuestRepository(session)
    rooms = RoomRepository(session)
    bookings = BookingRepository(session)
    guest = guests.create("Тест Тест", "t@example.com", "1")
    room = rooms.create("101", "Стандарт", 2, "1000")
    session.commit()

    bookings.create(guest.id, room.id, date(2025, 6, 1), date(2025, 6, 5), Decimal("4000"))
    session.commit()

    # пересечение "внутри" интервала
    assert bookings.find_overlapping(room.id, date(2025, 6, 3), date(2025, 6, 4))
    # пересечение по границе (заезд в день выезда) — не конфликт
    assert not bookings.find_overlapping(room.id, date(2025, 6, 5), date(2025, 6, 7))
    # бронь до интервала — не конфликт
    assert not bookings.find_overlapping(room.id, date(2025, 5, 20), date(2025, 6, 1))
    # полное накрытие
    assert bookings.find_overlapping(room.id, date(2025, 5, 30), date(2025, 6, 10))
    assert bookings.is_room_available(room.id, date(2025, 6, 5), date(2025, 6, 7)) is True


def test_find_available_rooms(session: Session) -> None:
    rooms = RoomRepository(session)
    guests = GuestRepository(session)
    bookings = BookingRepository(session)
    room1 = rooms.create("101", "Стандарт", 2, "3000")
    room2 = rooms.create("102", "Люкс", 4, "7000")
    room3 = rooms.create("103", "Эконом", 1, "1500", is_active=False)
    guest = guests.create("A", "a@example.com", "1")
    session.commit()

    bookings.create(guest.id, room1.id, date(2025, 6, 1), date(2025, 6, 5), Decimal("12000"))
    session.commit()

    available = rooms.find_available(date(2025, 6, 1), date(2025, 6, 5))
    numbers = [r.number for r in available]
    assert numbers == ["102"]  # 101 занят, 103 неактивен
    assert room2.id in [r.id for r in available]
    assert room3.id not in [r.id for r in available]

    available_capacity = rooms.find_available(date(2025, 6, 1), date(2025, 6, 5), min_capacity=4)
    assert [r.number for r in available_capacity] == ["102"]


def test_booking_filters_and_sorts(session: Session) -> None:
    rooms = RoomRepository(session)
    guests = GuestRepository(session)
    bookings = BookingRepository(session)
    room = rooms.create("101", "Стандарт", 4, "1000")
    guest = guests.create("A", "a@example.com", "1")
    session.commit()

    b1 = bookings.create(guest.id, room.id, date(2025, 6, 1), date(2025, 6, 3), Decimal("2000"))
    b2 = bookings.create(guest.id, room.id, date(2025, 7, 1), date(2025, 7, 5), Decimal("4000"))
    b3 = bookings.create(
        guest.id, room.id, date(2025, 8, 1), date(2025, 8, 2), Decimal("1000"),
        status=BookingStatus.CANCELLED.value,
    )
    session.commit()

    assert [b.id for b in bookings.list_filtered(status="active")] == [b1.id, b2.id]
    assert [b.id for b in bookings.list_filtered(min_price=3000)] == [b2.id]
    assert [b.id for b in bookings.list_filtered(date_from=date(2025, 7, 1))] == [b2.id, b3.id]

    assert [b.id for b in bookings.list_sorted_by_check_in()] == [b1.id, b2.id, b3.id]
    assert [b.id for b in bookings.list_sorted_by_total_price(descending=True)] == [b2.id, b1.id, b3.id]
    assert len(bookings.list_by_guest(guest.id)) == 3
    assert len(bookings.list_by_room(room.id)) == 3
