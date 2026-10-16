"""Репозиторий бронирований: пересечения периодов, фильтрация, статистика."""
from __future__ import annotations

from datetime import date

from sqlalchemy import Select, func, select
from sqlalchemy.orm import joinedload

from app.models import Booking, BookingStatus, Room
from app.repositories.base import SqlAlchemyRepository
from app.schemas.booking import BookingFilter, BookingSort

SORT_EXPRESSIONS = {
    BookingSort.CREATED_DESC: Booking.created_at.desc(),
    BookingSort.CHECK_IN_ASC: Booking.check_in.asc(),
    BookingSort.CHECK_IN_DESC: Booking.check_in.desc(),
    BookingSort.PRICE_DESC: Booking.price_total.desc(),
}


class BookingRepository(SqlAlchemyRepository[Booking]):
    model = Booking

    def get_with_relations(self, booking_id: int) -> Booking | None:
        statement = (
            select(Booking)
            .where(Booking.id == booking_id)
            .options(joinedload(Booking.room), joinedload(Booking.user))
        )
        return self.session.scalars(statement).first()

    def find_overlapping(self, room_id: int, check_in: date, check_out: date) -> Booking | None:
        """Найти подтверждённое бронирование, пересекающееся с периодом.

        Периоды считаются полуинтервалами [check_in, check_out), поэтому выезд
        в день заезда другого гостя конфликтом не является.
        """
        statement = (
            select(Booking)
            .where(
                Booking.room_id == room_id,
                Booking.status == BookingStatus.CONFIRMED,
                Booking.check_in < check_out,
                Booking.check_out > check_in,
            )
            .order_by(Booking.check_in)
            .limit(1)
        )
        return self.session.scalars(statement).first()

    def _filtered_statement(self, filters: BookingFilter) -> Select:
        statement = select(Booking).options(
            joinedload(Booking.room), joinedload(Booking.user)
        )
        if filters.status is not None:
            statement = statement.where(Booking.status == filters.status)
        if filters.user_id is not None:
            statement = statement.where(Booking.user_id == filters.user_id)
        if filters.room_id is not None:
            statement = statement.where(Booking.room_id == filters.room_id)
        if filters.check_in_from is not None:
            statement = statement.where(Booking.check_in >= filters.check_in_from)
        if filters.check_in_to is not None:
            statement = statement.where(Booking.check_in <= filters.check_in_to)
        return statement

    def search(self, filters: BookingFilter) -> tuple[list[Booking], int]:
        statement = self._filtered_statement(filters)
        total = int(
            self.session.scalar(select(func.count()).select_from(statement.subquery())) or 0
        )
        page_statement = (
            statement.order_by(SORT_EXPRESSIONS[filters.sort], Booking.id)
            .limit(filters.limit)
            .offset(filters.offset)
        )
        return list(self.session.scalars(page_statement).all()), total

    def status_counts(self) -> dict[str, int]:
        statement = select(Booking.status, func.count()).group_by(Booking.status)
        return {
            status.value if hasattr(status, "value") else str(status): int(count)
            for status, count in self.session.execute(statement).all()
        }

    def aggregates(self) -> dict[str, float]:
        statement = select(
            func.avg(Booking.price_total), func.avg(Booking.nights), func.count()
        )
        average_price, average_nights, total = self.session.execute(statement).one()
        return {
            "average_price": round(float(average_price or 0.0), 2),
            "average_nights": round(float(average_nights or 0.0), 2),
            "total": int(total or 0),
        }

    def most_popular_room_type(self) -> str | None:
        statement = (
            select(Room.room_type, func.count(Booking.id))
            .join(Booking, Booking.room_id == Room.id)
            .where(Booking.status != BookingStatus.CANCELLED)
            .group_by(Room.room_type)
            .order_by(func.count(Booking.id).desc())
            .limit(1)
        )
        row = self.session.execute(statement).first()
        if row is None or row[0] is None:
            return None
        room_type = row[0]
        return room_type.value if hasattr(room_type, "value") else str(room_type)
