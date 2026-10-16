"""Тесты сервисного слоя: транзакции бронирования, откаты, обработка ошибок."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.exceptions import (
    BookingConflictError,
    DuplicateError,
    NotEnoughCapacityError,
    NotFoundError,
    RoomUnavailableError,
    TransactionError,
    ValidationError,
)
from app.models.booking import BookingStatus
from app.repositories.booking_repository import BookingRepository
from app.services.hotel_service import HotelService


@pytest.fixture()
def guest_and_room(service: HotelService):
    guest = service.register_guest("Иванов Иван", "ivan@example.com", "+79001112233")
    room = service.add_room("101", "Стандарт", 2, "3000")
    return guest, room


def test_register_guest_and_duplicate(service: HotelService) -> None:
    service.register_guest("Иванов Иван", "ivan@example.com", "+79001112233")
    with pytest.raises(DuplicateError):
        service.register_guest("Другой Гость", "ivan@example.com", "+79000000000")
    assert len(service.list_guests()) == 1


def test_book_room_success(service: HotelService, guest_and_room) -> None:
    guest, room = guest_and_room
    result = service.book_room(guest.id, room.id, date(2025, 6, 1), date(2025, 6, 5), 2)
    assert result.nights == 4
    assert result.total_price == Decimal("12000.00")
    assert result.booking.id is not None
    assert result.booking.status == BookingStatus.ACTIVE.value
    assert "Бронь #" in result.describe()


def test_book_room_overlap_rolls_back(service: HotelService, guest_and_room, session) -> None:
    guest, room = guest_and_room
    service.book_room(guest.id, room.id, date(2025, 6, 1), date(2025, 6, 5), 1)
    repo = BookingRepository(session)
    before = repo.count()

    with pytest.raises(BookingConflictError):
        service.book_room(guest.id, room.id, date(2025, 6, 3), date(2025, 6, 7), 1)

    assert repo.count() == before  # откат: новая строка не появилась


def test_book_room_capacity_exceeded(service: HotelService, guest_and_room, session) -> None:
    guest, room = guest_and_room
    with pytest.raises(NotEnoughCapacityError):
        service.book_room(guest.id, room.id, date(2025, 6, 1), date(2025, 6, 3), 3)
    assert BookingRepository(session).count() == 0


def test_book_room_invalid_dates(service: HotelService, guest_and_room, session) -> None:
    guest, room = guest_and_room
    with pytest.raises(ValidationError):
        service.book_room(guest.id, room.id, date(2025, 6, 5), date(2025, 6, 1), 1)
    assert BookingRepository(session).count() == 0


def test_book_room_unknown_guest_or_room(service: HotelService, guest_and_room, session) -> None:
    guest, room = guest_and_room
    with pytest.raises(NotFoundError):
        service.book_room(999, room.id, date(2025, 6, 1), date(2025, 6, 3), 1)
    with pytest.raises(NotFoundError):
        service.book_room(guest.id, 999, date(2025, 6, 1), date(2025, 6, 3), 1)
    assert BookingRepository(session).count() == 0


def test_book_room_inactive_room(service: HotelService, guest_and_room) -> None:
    guest, room = guest_and_room
    service.update_room(room.id, is_active=False)
    with pytest.raises(RoomUnavailableError):
        service.book_room(guest.id, room.id, date(2025, 6, 1), date(2025, 6, 3), 1)


def test_available_rooms_and_filters(service: HotelService, guest_and_room) -> None:
    guest, room101 = guest_and_room
    room102 = service.add_room("102", "Люкс", 4, "7000")
    service.add_room("103", "Эконом", 1, "1500", is_active=False)
    service.book_room(guest.id, room101.id, date(2025, 6, 1), date(2025, 6, 5), 1)

    free = service.available_rooms(date(2025, 6, 1), date(2025, 6, 5))
    assert [r.number for r in free] == ["102"]
    assert service.available_rooms(date(2025, 6, 10), date(2025, 6, 12))
    assert [r.number for r in service.filter_rooms(is_active=False)] == ["103"]
    assert [r.number for r in service.filter_rooms(min_price=2000, max_price=5000)] == ["101"]
    assert room102.id is not None

    with pytest.raises(ValidationError):
        service.available_rooms(date(2025, 6, 5), date(2025, 6, 1))


def test_cancel_and_reschedule(service: HotelService, guest_and_room) -> None:
    guest, room = guest_and_room
    result = service.book_room(guest.id, room.id, date(2025, 6, 1), date(2025, 6, 5), 1)

    moved = service.reschedule_booking(result.booking.id, date(2025, 6, 10), date(2025, 6, 12))
    assert moved.check_in == date(2025, 6, 10)
    assert moved.total_price == Decimal("6000.00")

    cancelled = service.cancel_booking(result.booking.id)
    assert cancelled.status == BookingStatus.CANCELLED.value

    # отменённая бронь не мешает новому бронированию тех же дат
    service.book_room(guest.id, room.id, date(2025, 6, 10), date(2025, 6, 12), 1)


def test_reschedule_conflict(service: HotelService, guest_and_room) -> None:
    guest, room = guest_and_room
    first = service.book_room(guest.id, room.id, date(2025, 6, 1), date(2025, 6, 5), 1)
    second = service.book_room(guest.id, room.id, date(2025, 6, 10), date(2025, 6, 12), 1)
    with pytest.raises(BookingConflictError):
        service.reschedule_booking(second.booking.id, date(2025, 6, 3), date(2025, 6, 6))
    assert first.booking.id != second.booking.id


def test_change_status_validation(service: HotelService, guest_and_room) -> None:
    guest, room = guest_and_room
    result = service.book_room(guest.id, room.id, date(2025, 6, 1), date(2025, 6, 5), 1)
    with pytest.raises(ValidationError):
        service.change_booking_status(result.booking.id, "unknown-status")
    updated = service.change_booking_status(result.booking.id, BookingStatus.COMPLETED.value)
    assert updated.status == BookingStatus.COMPLETED.value


def test_delete_room_with_bookings_raises(service: HotelService, guest_and_room) -> None:
    guest, room = guest_and_room
    service.book_room(guest.id, room.id, date(2025, 6, 1), date(2025, 6, 5), 1)
    with pytest.raises(TransactionError):
        service.delete_room(room.id)


def test_delete_guest_cascades_bookings(service: HotelService, guest_and_room, session) -> None:
    guest, room = guest_and_room
    service.book_room(guest.id, room.id, date(2025, 6, 1), date(2025, 6, 5), 1)
    service.delete_guest(guest.id)
    assert len(service.list_guests()) == 0
    assert BookingRepository(session).count() == 0


def test_bookings_of_guest_and_room(service: HotelService, guest_and_room) -> None:
    guest, room = guest_and_room
    service.book_room(guest.id, room.id, date(2025, 6, 1), date(2025, 6, 5), 1)
    service.book_room(guest.id, room.id, date(2025, 7, 1), date(2025, 7, 3), 1)
    assert len(service.bookings_of_guest(guest.id)) == 2
    assert len(service.bookings_of_room(room.id)) == 2
    assert service.bookings_of_guest(guest.id)[0].room.number == "101"

    with pytest.raises(NotFoundError):
        service.bookings_of_guest(999)
    with pytest.raises(NotFoundError):
        service.get_booking(999)


def test_sorted_lists(service: HotelService, guest_and_room) -> None:
    guest, room = guest_and_room
    service.add_room("102", "Люкс", 4, "7000")
    assert [r.number for r in service.rooms_sorted_by_price()] == ["101", "102"]
    assert [r.number for r in service.rooms_sorted_by_capacity(descending=True)] == ["102", "101"]
    service.book_room(guest.id, room.id, date(2025, 6, 1), date(2025, 6, 5), 1)
    service.book_room(guest.id, room.id, date(2025, 7, 1), date(2025, 7, 2), 1)
    assert [b.check_in for b in service.bookings_sorted_by_check_in()] == [
        date(2025, 6, 1),
        date(2025, 7, 1),
    ]
    assert len(service.filter_bookings(status=BookingStatus.ACTIVE.value)) == 2
