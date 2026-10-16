"""Репозиторий бронирований: CRUD, поиск пересечений, фильтры, сортировки."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.exceptions import ValidationError
from app.models.booking import Booking, BookingStatus
from app.models.guest import Guest
from app.models.room import Room
from app.repositories.base import BaseRepository


class BookingRepository(BaseRepository[Booking]):
    """Операции доступа к данным таблицы bookings."""

    model = Booking

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def create(
        self,
        guest_id: int,
        room_id: int,
        check_in: date,
        check_out: date,
        total_price: Decimal | float,
        status: str = BookingStatus.ACTIVE.value,
    ) -> Booking:
        """Вставить бронь (без commit) и выполнить flush для получения id."""
        if check_out <= check_in:
            raise ValidationError("Дата выезда должна быть позже даты заезда")
        booking = Booking(
            guest_id=guest_id,
            room_id=room_id,
            check_in=check_in,
            check_out=check_out,
            status=status,
            total_price=Decimal(str(total_price)),
        )
        self.session.add(booking)
        self.session.flush()
        return booking

    def list_by_guest(self, guest_id: int) -> list[Booking]:
        """Все брони конкретного гостя (связанные объекты подгружаются joinedload)."""
        stmt = (
            select(Booking)
            .options(joinedload(Booking.room))
            .where(Booking.guest_id == guest_id)
            .order_by(Booking.check_in)
        )
        return list(self.session.scalars(stmt).unique().all())

    def list_by_room(self, room_id: int) -> list[Booking]:
        """Все брони конкретного номера."""
        stmt = (
            select(Booking)
            .options(joinedload(Booking.guest))
            .where(Booking.room_id == room_id)
            .order_by(Booking.check_in)
        )
        return list(self.session.scalars(stmt).unique().all())

    def list_filtered(
        self,
        status: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        min_price: Decimal | float | None = None,
        max_price: Decimal | float | None = None,
    ) -> list[Booking]:
        """Фильтрация броней по статусу, датам и диапазону стоимости (AND)."""
        stmt = select(Booking).options(joinedload(Booking.guest), joinedload(Booking.room))
        conditions = []
        if status:
            conditions.append(Booking.status == status)
        if date_from is not None:
            conditions.append(Booking.check_in >= date_from)
        if date_to is not None:
            conditions.append(Booking.check_out <= date_to)
        if min_price is not None:
            conditions.append(Booking.total_price >= Decimal(str(min_price)))
        if max_price is not None:
            conditions.append(Booking.total_price <= Decimal(str(max_price)))
        if conditions:
            stmt = stmt.where(*conditions)
        return list(self.session.scalars(stmt.order_by(Booking.check_in)).unique().all())

    def find_overlapping(
        self,
        room_id: int,
        check_in: date,
        check_out: date,
        exclude_booking_id: int | None = None,
        statuses: tuple[str, ...] = (BookingStatus.ACTIVE.value,),
    ) -> list[Booking]:
        """Найти активные брони номера, пересекающиеся с интервалом.

        Условие пересечения интервалов: existing.check_in < new.check_out
        И existing.check_out > new.check_in.
        """
        stmt = select(Booking).where(
            Booking.room_id == room_id,
            Booking.status.in_(statuses),
            Booking.check_in < check_out,
            Booking.check_out > check_in,
        )
        if exclude_booking_id is not None:
            stmt = stmt.where(Booking.id != exclude_booking_id)
        return list(self.session.scalars(stmt.order_by(Booking.check_in)).all())

    def is_room_available(
        self,
        room_id: int,
        check_in: date,
        check_out: date,
        exclude_booking_id: int | None = None,
    ) -> bool:
        """Свободен ли номер на заданные даты."""
        return not self.find_overlapping(room_id, check_in, check_out, exclude_booking_id)

    def list_sorted_by_check_in(self, descending: bool = False) -> list[Booking]:
        """Сортировка №1: по дате заезда."""
        order = Booking.check_in.desc() if descending else Booking.check_in.asc()
        return list(
            self.session.scalars(select(Booking).order_by(order, Booking.id)).all()
        )

    def list_sorted_by_total_price(self, descending: bool = True) -> list[Booking]:
        """Сортировка №2: по итоговой стоимости."""
        order = Booking.total_price.desc() if descending else Booking.total_price.asc()
        return list(
            self.session.scalars(select(Booking).order_by(order, Booking.id)).all()
        )

    def update_booking(
        self,
        booking: Booking,
        check_in: date | None = None,
        check_out: date | None = None,
        status: str | None = None,
        total_price: Decimal | float | None = None,
    ) -> Booking:
        """Изменить параметры брони."""
        payload: dict[str, object] = {}
        if check_in is not None:
            payload["check_in"] = check_in
        if check_out is not None:
            payload["check_out"] = check_out
        if status is not None:
            payload["status"] = status
        if total_price is not None:
            payload["total_price"] = Decimal(str(total_price))
        self.update(booking, **payload)
        return booking

    def guests_and_rooms_with_bookings(self) -> list[tuple[Guest, Room, Booking]]:
        """Получить связанные объекты одним запросом (JOIN трёх таблиц)."""
        stmt = (
            select(Guest, Room, Booking)
            .join(Booking, Booking.guest_id == Guest.id)
            .join(Room, Room.id == Booking.room_id)
            .order_by(Booking.id)
        )
        return [tuple(row) for row in self.session.execute(stmt).all()]  # type: ignore[misc]
