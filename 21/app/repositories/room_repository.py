"""Репозиторий гостиничных номеров: поиск, фильтрация и сортировка."""
from __future__ import annotations

from sqlalchemy import Select, func, select

from app.models import Booking, BookingStatus, Room, RoomStatus
from app.repositories.base import SqlAlchemyRepository
from app.schemas.room import RoomFilter, RoomSort

SORT_EXPRESSIONS = {
    RoomSort.NUMBER_ASC: Room.number.asc(),
    RoomSort.PRICE_ASC: Room.price_per_night.asc(),
    RoomSort.PRICE_DESC: Room.price_per_night.desc(),
    RoomSort.CAPACITY_DESC: Room.capacity.desc(),
}


class RoomRepository(SqlAlchemyRepository[Room]):
    model = Room

    def get_by_number(self, number: str) -> Room | None:
        statement = select(Room).where(Room.number == number.strip())
        return self.session.scalars(statement).first()

    def _filtered_statement(self, filters: RoomFilter) -> Select:
        statement = select(Room)
        if filters.room_type is not None:
            statement = statement.where(Room.room_type == filters.room_type)
        if filters.status is not None:
            statement = statement.where(Room.status == filters.status)
        if filters.min_price is not None:
            statement = statement.where(Room.price_per_night >= filters.min_price)
        if filters.max_price is not None:
            statement = statement.where(Room.price_per_night <= filters.max_price)
        if filters.min_capacity is not None:
            statement = statement.where(Room.capacity >= filters.min_capacity)
        if filters.floor is not None:
            statement = statement.where(Room.floor == filters.floor)
        return statement

    def search(self, filters: RoomFilter) -> tuple[list[Room], int]:
        """Вернуть страницу номеров и общее количество записей по фильтру."""
        statement = self._filtered_statement(filters)
        total = int(
            self.session.scalar(
                select(func.count()).select_from(statement.subquery())
            )
            or 0
        )
        ordering = SORT_EXPRESSIONS[filters.sort]
        page_statement = statement.order_by(ordering, Room.id).limit(filters.limit).offset(filters.offset)
        return list(self.session.scalars(page_statement).all()), total

    def available_between(
        self,
        check_in,
        check_out,
        *,
        min_capacity: int | None = None,
        room_type=None,
    ) -> list[Room]:
        """Номера, доступные к проживанию в указанном периоде.

        Учитываются только доступные номера, для которых нет пересекающегося
        подтверждённого бронирования.
        """
        occupied = (
            select(Booking.room_id)
            .where(
                Booking.status == BookingStatus.CONFIRMED,
                Booking.check_in < check_out,
                Booking.check_out > check_in,
            )
            .scalar_subquery()
        )
        statement = (
            select(Room)
            .where(Room.status == RoomStatus.AVAILABLE, Room.id.not_in(occupied))
            .order_by(Room.price_per_night.asc(), Room.id)
        )
        if min_capacity is not None:
            statement = statement.where(Room.capacity >= min_capacity)
        if room_type is not None:
            statement = statement.where(Room.room_type == room_type)
        return list(self.session.scalars(statement).all())

    def has_active_bookings(self, room_id: int) -> bool:
        statement = (
            select(func.count())
            .select_from(Booking)
            .where(
                Booking.room_id == room_id,
                Booking.status == BookingStatus.CONFIRMED,
                Booking.check_out >= func.current_date(),
            )
        )
        return int(self.session.scalar(statement) or 0) > 0

    def status_counts(self) -> dict[str, int]:
        statement = select(Room.status, func.count()).group_by(Room.status)
        return {
            status.value if hasattr(status, "value") else str(status): int(count)
            for status, count in self.session.execute(statement).all()
        }
