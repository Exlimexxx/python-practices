"""Модульные тесты репозиториев: фильтры, сортировка и агрегаты."""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models import Booking, BookingStatus, Payment, PaymentMethod, PaymentStatus, Room, RoomStatus, RoomType, User, UserRole
from app.repositories.booking_repository import BookingRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.room_repository import RoomRepository
from app.schemas.booking import BookingFilter, BookingSort
from app.schemas.room import RoomFilter, RoomSort

TODAY = date.today()


def make_user(session: Session, email: str = "repo@example.com") -> User:
    user = User(
        email=email,
        full_name="Репозиторный Тест",
        password_hash="pbkdf2_sha256$1$AA$BB",
        role=UserRole.USER,
    )
    session.add(user)
    session.commit()
    return user


def make_room(session: Session, number: str, price: float, room_type: RoomType = RoomType.STANDARD) -> Room:
    room = Room(number=number, room_type=room_type, capacity=2, price_per_night=price, floor=1)
    session.add(room)
    session.commit()
    return room


def make_booking(
    session: Session,
    user: User,
    room: Room,
    check_in: date,
    check_out: date,
    status: BookingStatus = BookingStatus.CONFIRMED,
) -> Booking:
    nights = (check_out - check_in).days
    booking = Booking(
        user_id=user.id,
        room_id=room.id,
        check_in=check_in,
        check_out=check_out,
        nights=nights,
        price_total=round(room.price_per_night * nights, 2),
        status=status,
    )
    session.add(booking)
    session.commit()
    return booking


def test_room_repository_filters_and_sorts(session: Session):
    make_room(session, "101", 3000, RoomType.STANDARD)
    make_room(session, "102", 12000, RoomType.LUX)
    make_room(session, "103", 8000, RoomType.LUX)
    repository = RoomRepository(session)

    lux_page, total = repository.search(RoomFilter(room_type=RoomType.LUX))
    assert total == 2
    assert [room.number for room in lux_page] == ["102", "103"]

    sorted_page, _ = repository.search(
        RoomFilter(room_type=RoomType.LUX, sort=RoomSort.PRICE_ASC)
    )
    assert [room.number for room in sorted_page] == ["103", "102"]

    filtered, _ = repository.search(RoomFilter(min_price=5000, min_capacity=2))
    assert {room.number for room in filtered} == {"102", "103"}


def test_room_repository_detects_active_bookings(session: Session):
    user = make_user(session)
    room = make_room(session, "201", 5000)
    repository = RoomRepository(session)

    make_booking(session, user, room, TODAY + timedelta(days=1), TODAY + timedelta(days=3))
    assert repository.has_active_bookings(room.id) is True

    make_booking(
        session,
        user,
        room,
        TODAY + timedelta(days=10),
        TODAY + timedelta(days=12),
        status=BookingStatus.CANCELLED,
    )
    other_room = make_room(session, "202", 6000)
    assert repository.has_active_bookings(other_room.id) is False


def test_booking_repository_ignores_cancelled_bookings_in_overlap(session: Session):
    user = make_user(session)
    room = make_room(session, "301", 7000)
    repository = BookingRepository(session)

    make_booking(
        session,
        user,
        room,
        TODAY + timedelta(days=5),
        TODAY + timedelta(days=8),
        status=BookingStatus.CANCELLED,
    )
    assert repository.find_overlapping(room.id, TODAY + timedelta(days=5), TODAY + timedelta(days=7)) is None

    active = make_booking(
        session, user, room, TODAY + timedelta(days=5), TODAY + timedelta(days=8)
    )
    found = repository.find_overlapping(room.id, TODAY + timedelta(days=6), TODAY + timedelta(days=9))
    assert found is not None and found.id == active.id

    adjacent = repository.find_overlapping(room.id, TODAY + timedelta(days=8), TODAY + timedelta(days=10))
    assert adjacent is None


def test_booking_repository_search_filters_and_aggregates(session: Session):
    user = make_user(session)
    room = make_room(session, "401", 4000)
    repository = BookingRepository(session)

    first = make_booking(session, user, room, TODAY + timedelta(days=1), TODAY + timedelta(days=3))
    second = make_booking(session, user, room, TODAY + timedelta(days=20), TODAY + timedelta(days=24))
    make_booking(
        session,
        user,
        room,
        TODAY + timedelta(days=40),
        TODAY + timedelta(days=41),
        status=BookingStatus.CANCELLED,
    )

    page, total = repository.search(BookingFilter(status=BookingStatus.CONFIRMED))
    assert total == 2

    ordered, _ = repository.search(BookingFilter(sort=BookingSort.PRICE_DESC))
    assert ordered[0].id == second.id

    window, _ = repository.search(
        BookingFilter(check_in_from=TODAY + timedelta(days=15), check_in_to=TODAY + timedelta(days=30))
    )
    assert [item.id for item in window] == [second.id]

    aggregates = repository.aggregates()
    assert aggregates["total"] == 3
    assert aggregates["average_nights"] > 0

    counts = repository.status_counts()
    assert counts == {"confirmed": 2, "cancelled": 1}
    assert repository.most_popular_room_type() == "standard"
    assert first.id != second.id


def test_payment_repository_totals(session: Session):
    user = make_user(session)
    room = make_room(session, "501", 3000)
    booking = make_booking(session, user, room, TODAY + timedelta(days=2), TODAY + timedelta(days=4))
    repository = PaymentRepository(session)

    paid = Payment(
        booking_id=booking.id,
        amount=2000.0,
        method=PaymentMethod.CARD,
        status=PaymentStatus.PAID,
    )
    refunded = Payment(
        booking_id=booking.id,
        amount=500.0,
        method=PaymentMethod.CASH,
        status=PaymentStatus.REFUNDED,
    )
    session.add_all([paid, refunded])
    session.commit()

    assert repository.paid_total(booking.id) == 2000.0
    assert repository.paid_totals_map([booking.id]) == {booking.id: 2000.0}
    assert repository.paid_totals_map([]) == {}
    assert repository.totals() == {"paid": 2000.0, "refunded": 500.0}
    assert [item.id for item in repository.list_for_booking(booking.id)] == [paid.id, refunded.id]


def test_room_repository_unavailable_rooms_are_excluded(session: Session):
    available = make_room(session, "601", 3500)
    maintenance = make_room(session, "602", 3600)
    maintenance.status = RoomStatus.MAINTENANCE
    session.commit()

    free = RoomRepository(session).available_between(
        TODAY + timedelta(days=1), TODAY + timedelta(days=2)
    )
    assert [room.number for room in free] == [available.number]
