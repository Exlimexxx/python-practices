"""Модульные тесты сервисов и работы с Mock-объектами."""
from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from sqlalchemy.orm import Session

from app.exceptions import (
    BookingOverlapError,
    EmailAlreadyUsedError,
    PaymentAmountError,
    RoomHasBookingsError,
    RoomNotFoundError,
)
from app.models import Booking, BookingStatus, Room, RoomStatus, User, UserRole
from app.repositories.booking_repository import BookingRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.room_repository import RoomRepository
from app.repositories.user_repository import UserRepository
from app.schemas.booking import BookingCreate
from app.schemas.payment import PaymentCreate
from app.schemas.room import RoomCreate, RoomFilter
from app.schemas.user import UserRegister
from app.services.booking_service import BookingService
from app.services.payment_service import PaymentService
from app.services.room_service import RoomService
from app.services.user_service import UserService
from tests.helpers import future_period


def test_booking_service_calculates_price_and_stores_nights(booking_service, room_service, actor):
    room = room_service.create_room(
        RoomCreate(number="701", capacity=2, price_per_night=3200.5, floor=7)
    )
    check_in, check_out = future_period(nights=3)
    created = booking_service.create_booking(
        BookingCreate(room_id=room.id, check_in=check_in, check_out=check_out), actor
    )
    assert created.nights == 3
    assert created.price_total == pytest.approx(3 * 3200.5)
    assert created.remaining_amount == created.price_total
    assert created.user_id == actor.id


def test_booking_service_rejects_room_that_does_not_exist(booking_service, actor):
    rooms = Mock(spec=RoomRepository)
    rooms.get.return_value = None
    session = Mock(spec=Session)
    service = BookingService(
        session, Mock(spec=BookingRepository), rooms, Mock(spec=PaymentRepository)
    )
    check_in, check_out = future_period()
    with pytest.raises(RoomNotFoundError):
        service.create_booking(
            BookingCreate(room_id=42, check_in=check_in, check_out=check_out), actor
        )
    session.add.assert_not_called()


def test_booking_service_detects_overlap_using_repository_mock(actor):
    room = SimpleNamespace(
        id=5, number="505", price_per_night=4000.0, status=RoomStatus.AVAILABLE
    )
    rooms = Mock(spec=RoomRepository)
    rooms.get.return_value = room
    bookings = Mock(spec=BookingRepository)
    bookings.find_overlapping.return_value = SimpleNamespace(
        id=99, check_in=future_period()[0], check_out=future_period()[1]
    )
    session = Mock(spec=Session)
    service = BookingService(session, bookings, rooms, Mock(spec=PaymentRepository))

    check_in, check_out = future_period()
    with pytest.raises(BookingOverlapError) as error:
        service.create_booking(
            BookingCreate(room_id=room.id, check_in=check_in, check_out=check_out), actor
        )
    assert error.value.details["conflicting_booking_id"] == 99
    session.add.assert_not_called()


def test_booking_service_persists_entity_through_repository_mock(actor):
    room = SimpleNamespace(
        id=5, number="505", price_per_night=2500.0, status=RoomStatus.AVAILABLE
    )
    captured: dict[str, Booking] = {}

    def fake_add(entity: Booking) -> Booking:
        entity.id = 17
        entity.created_at = datetime.now(timezone.utc)
        captured["booking"] = entity
        return entity

    rooms = Mock(spec=RoomRepository)
    rooms.get.return_value = room
    bookings = Mock(spec=BookingRepository)
    bookings.find_overlapping.return_value = None
    bookings.add.side_effect = fake_add
    bookings.get_with_relations.side_effect = lambda booking_id: captured["booking"]
    session = Mock(spec=Session)

    service = BookingService(session, bookings, rooms, Mock(spec=PaymentRepository))
    check_in, check_out = future_period(nights=2)
    created = service.create_booking(
        BookingCreate(room_id=room.id, check_in=check_in, check_out=check_out), actor
    )

    stored = captured["booking"]
    assert stored.nights == 2
    assert stored.price_total == pytest.approx(5000.0)
    assert stored.user_id == actor.id
    assert created.status is BookingStatus.CONFIRMED
    session.commit.assert_called_once()


def test_payment_service_rejects_overpayment_with_mock(actor):
    booking = SimpleNamespace(
        id=3, user_id=actor.id, status=BookingStatus.CONFIRMED, price_total=1000.0
    )
    bookings = Mock(spec=BookingRepository)
    bookings.get_with_relations.return_value = booking
    payments = Mock(spec=PaymentRepository)
    payments.paid_total.return_value = 800.0
    session = Mock(spec=Session)
    service = PaymentService(session, payments, bookings)

    with pytest.raises(PaymentAmountError) as error:
        service.pay(PaymentCreate(booking_id=3, amount=500.0), actor)
    assert error.value.details["remaining_amount"] == pytest.approx(200.0)
    session.add.assert_not_called()


def test_room_service_reports_page_from_repository_mock():
    filters = RoomFilter(limit=5, offset=0)
    rooms = Mock(spec=RoomRepository)
    rooms.search.return_value = (
        [
            SimpleNamespace(
                id=1,
                number="101",
                room_type="standard",
                capacity=2,
                price_per_night=3000.0,
                floor=1,
                status=RoomStatus.AVAILABLE,
                description=None,
                created_at=datetime.now(timezone.utc),
            )
        ],
        1,
    )
    service = RoomService(Mock(spec=Session), rooms)
    page = service.search_rooms(filters)

    rooms.search.assert_called_once_with(filters)
    assert page.total == 1
    assert page.items[0].number == "101"


def test_room_service_blocks_deletion_using_repository_mock():
    rooms = Mock(spec=RoomRepository)
    rooms.get.return_value = SimpleNamespace(id=8, number="808")
    rooms.has_active_bookings.return_value = True
    service = RoomService(Mock(spec=Session), rooms)
    with pytest.raises(RoomHasBookingsError):
        service.delete_room(8)


def test_user_service_detects_duplicate_email_using_repository_mock(settings):
    users = Mock(spec=UserRepository)
    users.get_by_email.return_value = SimpleNamespace(id=1, email="dup@example.com")
    session = Mock(spec=Session)
    service = UserService(session, users, settings)

    with pytest.raises(EmailAlreadyUsedError):
        service.register(
            UserRegister(email="dup@example.com", full_name="Дубль", password="dup-pass-123")
        )
    session.commit.assert_not_called()


def test_user_service_hashes_password_and_never_stores_plain_text(session, user_service):
    created = user_service.register(
        UserRegister(email="hash@example.com", full_name="Хеш Тестов", password="hash-pass-123")
    )
    stored = UserRepository(session).get(created.id)
    assert stored is not None
    assert stored.password_hash != "hash-pass-123"
    assert stored.password_hash.startswith("pbkdf2_sha256$")
    assert stored.role is UserRole.USER


def test_room_entity_keeps_status_and_constraints(session, room_service):
    room = room_service.create_room(
        RoomCreate(number="909", room_type="family", capacity=4, price_per_night=6100, floor=9)
    )
    stored = session.get(Room, room.id)
    assert stored is not None
    assert stored.number == "909"
    assert stored.status is RoomStatus.AVAILABLE

    user = User(
        email="owner@example.com",
        full_name="Владелец",
        password_hash="pbkdf2_sha256$1$AA$BB",
        role=UserRole.ADMIN,
    )
    session.add(user)
    session.commit()
    assert user.id is not None
