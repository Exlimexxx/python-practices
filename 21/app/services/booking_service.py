"""Сервис бронирований: правила доступности, пересечений и статусов."""
from __future__ import annotations

import logging
from datetime import date

from sqlalchemy.orm import Session

from app.exceptions import (
    BookingNotFoundError,
    BookingNotPaidError,
    BookingOverlapError,
    BookingStatusError,
    RoomNotAvailableError,
    RoomNotFoundError,
    ValidationFailure,
)
from app.models import Booking, BookingStatus, Room, RoomStatus, User, UserRole
from app.repositories.booking_repository import BookingRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.room_repository import RoomRepository
from app.schemas.booking import BookingCreate, BookingFilter, BookingOut, BookingPage
from app.services.permissions import ensure_owner_or_admin, require_authenticated_user

logger = logging.getLogger(__name__)

MONEY_TOLERANCE = 0.01


def to_booking_out(booking: Booking, paid_total: float) -> BookingOut:
    """Собрать схему ответа, дописав суммы платежей."""
    remaining = max(booking.price_total - paid_total, 0.0)
    return BookingOut(
        id=booking.id,
        user_id=booking.user_id,
        user_email=booking.user.email if booking.user is not None else "",
        room_id=booking.room_id,
        room_number=booking.room.number if booking.room is not None else "",
        check_in=booking.check_in,
        check_out=booking.check_out,
        nights=booking.nights,
        price_total=booking.price_total,
        paid_total=round(paid_total, 2),
        remaining_amount=round(remaining, 2),
        status=booking.status,
        comment=booking.comment,
        created_at=booking.created_at,
    )


class BookingService:
    """Создание, поиск и изменение состояния бронирований."""

    def __init__(
        self,
        session: Session,
        bookings: BookingRepository,
        rooms: RoomRepository,
        payments: PaymentRepository,
    ) -> None:
        self.session = session
        self.bookings = bookings
        self.rooms = rooms
        self.payments = payments

    def _get_booking(self, booking_id: int) -> Booking:
        booking = self.bookings.get_with_relations(booking_id)
        if booking is None:
            raise BookingNotFoundError(
                f"Бронирование с идентификатором {booking_id} не найдено",
                details={"booking_id": booking_id},
            )
        return booking

    @staticmethod
    def _ensure_room_available(room: Room) -> None:
        if room.status is not RoomStatus.AVAILABLE:
            raise RoomNotAvailableError(
                f"Номер {room.number} недоступен для бронирования (статус: {room.status.value})",
                details={"room_id": room.id, "status": room.status.value},
            )

    @staticmethod
    def _ensure_period_is_future(check_in: date) -> None:
        if check_in < date.today():
            raise ValidationFailure(
                "Дата заезда не может быть в прошлом",
                details={"check_in": check_in.isoformat()},
            )

    def create_booking(self, payload: BookingCreate, actor: User | None) -> BookingOut:
        """Создать бронирование, проверив номер, период и пересечения."""
        user = require_authenticated_user(actor)
        room = self.rooms.get(payload.room_id)
        if room is None:
            raise RoomNotFoundError(
                f"Номер с идентификатором {payload.room_id} не найден",
                details={"room_id": payload.room_id},
            )
        self._ensure_period_is_future(payload.check_in)
        self._ensure_room_available(room)
        overlap = self.bookings.find_overlapping(room.id, payload.check_in, payload.check_out)
        if overlap is not None:
            raise BookingOverlapError(
                "Период пересекается с существующим подтверждённым бронированием",
                details={
                    "room_id": room.id,
                    "conflicting_booking_id": overlap.id,
                    "conflicting_period": [
                        overlap.check_in.isoformat(),
                        overlap.check_out.isoformat(),
                    ],
                },
            )
        nights = (payload.check_out - payload.check_in).days
        booking = Booking(
            user_id=user.id,
            room_id=room.id,
            check_in=payload.check_in,
            check_out=payload.check_out,
            nights=nights,
            price_total=round(room.price_per_night * nights, 2),
            status=BookingStatus.CONFIRMED,
            comment=payload.comment,
        )
        self.bookings.add(booking)
        self.session.commit()
        logger.info(
            "Создано бронирование id=%s room_id=%s user_id=%s nights=%s",
            booking.id,
            booking.room_id,
            booking.user_id,
            booking.nights,
        )
        return to_booking_out(self._get_booking(booking.id), 0.0)

    def get_booking(self, booking_id: int, actor: User | None) -> BookingOut:
        booking = self._get_booking(booking_id)
        ensure_owner_or_admin(booking.user_id, actor, entity="booking")
        paid = self.payments.paid_total(booking.id)
        return to_booking_out(booking, paid)

    def list_bookings(self, filters: BookingFilter, actor: User | None) -> BookingPage:
        user = require_authenticated_user(actor)
        if user.role is not UserRole.ADMIN:
            filters = filters.model_copy(update={"user_id": user.id})
        items, total = self.bookings.search(filters)
        paid_map = self.payments.paid_totals_map([booking.id for booking in items])
        return BookingPage(
            total=total,
            limit=filters.limit,
            offset=filters.offset,
            items=[to_booking_out(booking, paid_map.get(booking.id, 0.0)) for booking in items],
        )

    def cancel_booking(self, booking_id: int, actor: User | None, *, reason: str | None = None) -> BookingOut:
        booking = self._get_booking(booking_id)
        ensure_owner_or_admin(booking.user_id, actor, entity="booking")
        if booking.status is not BookingStatus.CONFIRMED:
            raise BookingStatusError(
                f"Отменить можно только подтверждённое бронирование (статус: {booking.status.value})",
                details={"booking_id": booking.id, "status": booking.status.value},
            )
        paid = self.payments.paid_total(booking.id)
        if paid > MONEY_TOLERANCE:
            raise BookingStatusError(
                "Нельзя отменить оплаченное бронирование: сначала оформите возврат платежей",
                details={"booking_id": booking.id, "paid_total": paid},
            )
        booking.status = BookingStatus.CANCELLED
        if reason:
            booking.comment = reason.strip()
        self.session.commit()
        logger.info("Отменено бронирование id=%s", booking.id)
        return to_booking_out(booking, 0.0)

    def complete_booking(self, booking_id: int) -> BookingOut:
        """Завершить проживание: доступно администратору для оплаченного бронирования."""
        booking = self._get_booking(booking_id)
        if booking.status is BookingStatus.CANCELLED:
            raise BookingStatusError("Отменённое бронирование нельзя завершить")
        if booking.status is BookingStatus.COMPLETED:
            raise BookingStatusError("Бронирование уже завершено")
        paid = self.payments.paid_total(booking.id)
        if booking.price_total - paid > MONEY_TOLERANCE:
            raise BookingNotPaidError(
                "Завершить можно только полностью оплаченное бронирование",
                details={
                    "booking_id": booking.id,
                    "remaining_amount": round(booking.price_total - paid, 2),
                },
            )
        booking.status = BookingStatus.COMPLETED
        self.session.commit()
        logger.info("Завершено бронирование id=%s", booking.id)
        return to_booking_out(booking, paid)
