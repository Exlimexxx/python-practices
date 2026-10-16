"""Сервис платежей по бронированиям."""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.exceptions import (
    BookingNotFoundError,
    BookingStatusError,
    PaymentAmountError,
    PaymentNotFoundError,
)
from app.models import Booking, BookingStatus, Payment, PaymentStatus, User
from app.repositories.booking_repository import BookingRepository
from app.repositories.payment_repository import PaymentRepository
from app.schemas.payment import PaymentCreate, PaymentOut
from app.services.permissions import ensure_owner_or_admin, require_authenticated_user

logger = logging.getLogger(__name__)

MONEY_TOLERANCE = 0.01


def to_payment_out(payment: Payment) -> PaymentOut:
    return PaymentOut(
        id=payment.id,
        booking_id=payment.booking_id,
        amount=payment.amount,
        method=payment.method,
        status=payment.status,
        created_at=payment.created_at,
    )


class PaymentService:
    """Приём оплаты и возврат средств."""

    def __init__(
        self,
        session: Session,
        payments: PaymentRepository,
        bookings: BookingRepository,
    ) -> None:
        self.session = session
        self.payments = payments
        self.bookings = bookings

    def _get_booking(self, booking_id: int) -> Booking:
        booking = self.bookings.get_with_relations(booking_id)
        if booking is None:
            raise BookingNotFoundError(
                f"Бронирование с идентификатором {booking_id} не найдено",
                details={"booking_id": booking_id},
            )
        return booking

    def pay(self, payload: PaymentCreate, actor: User | None) -> PaymentOut:
        """Оплатить бронирование частями, не превышая его стоимость."""
        user = require_authenticated_user(actor)
        booking = self._get_booking(payload.booking_id)
        ensure_owner_or_admin(booking.user_id, user, entity="booking")
        if booking.status is BookingStatus.CANCELLED:
            raise BookingStatusError(
                "Оплата отменённого бронирования невозможна",
                details={"booking_id": booking.id, "status": booking.status.value},
            )
        if booking.status is BookingStatus.COMPLETED:
            raise BookingStatusError("Бронирование уже завершено и закрыто для оплаты")
        paid_total = self.payments.paid_total(booking.id)
        remaining = round(booking.price_total - paid_total, 2)
        if remaining <= MONEY_TOLERANCE:
            raise PaymentAmountError(
                "Бронирование оплачено полностью", details={"remaining_amount": remaining}
            )
        if payload.amount - remaining > MONEY_TOLERANCE:
            raise PaymentAmountError(
                f"Сумма платежа превышает остаток к оплате ({remaining})",
                details={
                    "price_total": booking.price_total,
                    "paid_total": paid_total,
                    "remaining_amount": remaining,
                },
            )
        payment = Payment(
            booking_id=booking.id,
            amount=round(payload.amount, 2),
            method=payload.method,
            status=PaymentStatus.PAID,
        )
        self.payments.add(payment)
        self.session.commit()
        logger.info(
            "Принят платёж id=%s booking_id=%s amount=%s",
            payment.id,
            payment.booking_id,
            payment.amount,
        )
        return to_payment_out(payment)

    def get_payment(self, payment_id: int) -> Payment:
        payment = self.payments.get(payment_id)
        if payment is None:
            raise PaymentNotFoundError(
                f"Платёж с идентификатором {payment_id} не найден",
                details={"payment_id": payment_id},
            )
        return payment

    def refund(self, payment_id: int) -> PaymentOut:
        """Возврат средств: только для успешного платежа, доступен администратору."""
        payment = self.get_payment(payment_id)
        if payment.status is PaymentStatus.REFUNDED:
            raise BookingStatusError(
                "Платёж уже возвращён", details={"payment_id": payment.id}
            )
        payment.status = PaymentStatus.REFUNDED
        self.session.commit()
        logger.info("Оформлен возврат по платежу id=%s", payment.id)
        return to_payment_out(payment)

    def list_for_booking(self, booking_id: int, actor: User | None) -> list[PaymentOut]:
        user = require_authenticated_user(actor)
        booking = self._get_booking(booking_id)
        ensure_owner_or_admin(booking.user_id, user, entity="booking")
        return [to_payment_out(item) for item in self.payments.list_for_booking(booking.id)]

    def list_payments(self, *, limit: int = 50, offset: int = 0) -> tuple[list[PaymentOut], int]:
        items, total = self.payments.list_page(limit=limit, offset=offset)
        return [to_payment_out(item) for item in items], total
