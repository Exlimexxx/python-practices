"""Репозиторий платежей."""
from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func, select

from app.models import Payment, PaymentStatus
from app.repositories.base import SqlAlchemyRepository

CENT = 0.01


class PaymentRepository(SqlAlchemyRepository[Payment]):
    model = Payment

    def paid_total(self, booking_id: int) -> float:
        """Сумма успешных платежей по бронированию."""
        statement = select(func.coalesce(func.sum(Payment.amount), 0.0)).where(
            Payment.booking_id == booking_id,
            Payment.status == PaymentStatus.PAID,
        )
        return round(float(self.session.scalar(statement) or 0.0), 2)

    def paid_totals_map(self, booking_ids: Sequence[int]) -> dict[int, float]:
        """Суммы успешных платежей сразу по нескольким бронированиям."""
        if not booking_ids:
            return {}
        statement = (
            select(Payment.booking_id, func.coalesce(func.sum(Payment.amount), 0.0))
            .where(
                Payment.booking_id.in_(list(booking_ids)),
                Payment.status == PaymentStatus.PAID,
            )
            .group_by(Payment.booking_id)
        )
        return {
            int(booking_id): round(float(total), 2)
            for booking_id, total in self.session.execute(statement).all()
        }

    def list_for_booking(self, booking_id: int) -> list[Payment]:
        statement = (
            select(Payment).where(Payment.booking_id == booking_id).order_by(Payment.id)
        )
        return list(self.session.scalars(statement).all())

    def list_page(self, *, limit: int = 100, offset: int = 0) -> tuple[list[Payment], int]:
        total = self.count()
        statement = select(Payment).order_by(Payment.id).limit(limit).offset(offset)
        return list(self.session.scalars(statement).all()), total

    def totals(self) -> dict[str, float]:
        """Суммы оплаченных и возвращённых средств."""
        statement = select(Payment.status, func.coalesce(func.sum(Payment.amount), 0.0)).group_by(
            Payment.status
        )
        result = {"paid": 0.0, "refunded": 0.0}
        for status, total in self.session.execute(statement).all():
            key = status.value if hasattr(status, "value") else str(status)
            result[key] = round(float(total), 2)
        return result
