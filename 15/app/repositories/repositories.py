"""Репозитории — слой доступа к данным (инкапсулируют SQLAlchemy-запросы).

Согласно п. 10 методички SQLAlchemy-запросы не должны размещаться в
обработчиках Flask: маршруты вызывают сервисы, сервисы — репозитории.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Sequence

from sqlalchemy import Select, func, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.exceptions import ConflictError, PersistenceError
from app.models import Booking, Guest, Room

logger = logging.getLogger(__name__)


class BaseRepository:
    """Общая функциональность репозиториев: работа с сессией и коммитами."""

    model: type

    def __init__(self, session: Session) -> None:
        self.session = session

    def _commit(self, entity: object) -> object:
        """Фиксирует транзакцию и обрабатывает ошибки целостности."""
        try:
            self.session.commit()
        except IntegrityError as exc:  # нарушение UNIQUE/CHECK
            self.session.rollback()
            logger.warning("Нарушено ограничение целостности: %s", exc.orig)
            raise ConflictError("Нарушено ограничение уникальности данных") from exc
        except SQLAlchemyError as exc:
            self.session.rollback()
            logger.exception("Ошибка сохранения в БД")
            raise PersistenceError() from exc
        self.session.refresh(entity)
        return entity

    def delete(self, entity: object) -> None:
        """Удаляет объект и фиксирует транзакцию."""
        self.session.delete(entity)
        try:
            self.session.commit()
        except SQLAlchemyError as exc:
            self.session.rollback()
            logger.exception("Ошибка удаления из БД")
            raise PersistenceError() from exc

    def add(self, entity: object) -> object:
        """Добавляет объект и фиксирует транзакцию."""
        self.session.add(entity)
        return self._commit(entity)

    def _search(self, columns: list, search: str):
        """Регистронезависимый поиск по подстроке.

        В SQLite встроенный LIKE не учитывает регистр кириллицы, поэтому для
        этого диалекта используется зарегистрированная функция u_lower.
        """
        pattern = f"%{search.strip()}%"
        dialect = self.session.get_bind().dialect.name
        if dialect == "sqlite":
            return or_(*[func.u_lower(column).like(func.u_lower(pattern)) for column in columns])
        return or_(*[column.ilike(pattern) for column in columns])


class RoomRepository(BaseRepository):
    """Запросы по номерам отеля."""

    model = Room

    def get(self, room_id: int) -> Room | None:
        """Возвращает номер по идентификатору."""
        return self.session.get(Room, room_id)

    def get_by_number(self, number: str) -> Room | None:
        """Возвращает номер по его строковому номеру."""
        return self.session.scalar(select(Room).where(Room.number == number))

    def list(
        self,
        *,
        search: str | None = None,
        room_type: str | None = None,
        is_active: bool | None = None,
        min_capacity: int | None = None,
        sort: str = "number",
        order: str = "asc",
    ) -> Sequence[Room]:
        """Возвращает номера с поиском, фильтрацией и сортировкой."""
        stmt: Select = select(Room)
        if search:
            stmt = stmt.where(
                self._search([Room.number, Room.room_type, Room.description], search)
            )
        if room_type:
            stmt = stmt.where(Room.room_type == room_type)
        if is_active is not None:
            stmt = stmt.where(Room.is_active.is_(is_active))
        if min_capacity is not None:
            stmt = stmt.where(Room.capacity >= min_capacity)
        stmt = self._apply_sort(stmt, sort, order)
        return list(self.session.scalars(stmt).all())

    @staticmethod
    def _apply_sort(stmt: Select, sort: str, order: str) -> Select:
        """Применяет безопасную сортировку по белому списку колонок."""
        columns = {
            "number": Room.number,
            "price": Room.price_per_night,
            "capacity": Room.capacity,
            "floor": Room.floor,
            "id": Room.id,
        }
        column = columns.get(sort, Room.number)
        column = column.desc() if order == "desc" else column.asc()
        return stmt.order_by(column)

    def count(self) -> int:
        """Общее количество номеров."""
        return int(self.session.scalar(select(func.count(Room.id))) or 0)

    def count_active(self) -> int:
        """Количество доступных номеров."""
        return int(
            self.session.scalar(select(func.count(Room.id)).where(Room.is_active.is_(True))) or 0
        )


class GuestRepository(BaseRepository):
    """Запросы по гостям."""

    model = Guest

    def get(self, guest_id: int) -> Guest | None:
        """Возвращает гостя по идентификатору."""
        return self.session.get(Guest, guest_id)

    def get_by_email(self, email: str) -> Guest | None:
        """Возвращает гостя по email."""
        return self.session.scalar(select(Guest).where(Guest.email == email))

    def list(
        self,
        *,
        search: str | None = None,
        city: str | None = None,
        has_bookings: bool | None = None,
        sort: str = "full_name",
        order: str = "asc",
    ) -> Sequence[Guest]:
        """Возвращает гостей с поиском, фильтрацией и сортировкой."""
        stmt: Select = select(Guest)
        if search:
            stmt = stmt.where(self._search([Guest.full_name, Guest.email, Guest.phone], search))
        if city:
            stmt = stmt.where(Guest.city == city)
        if has_bookings is True:
            stmt = stmt.where(Guest.bookings.any())
        elif has_bookings is False:
            stmt = stmt.where(~Guest.bookings.any())
        columns = {
            "name": Guest.full_name,
            "email": Guest.email,
            "city": Guest.city,
            "id": Guest.id,
        }
        column = columns.get(sort, Guest.full_name)
        stmt = stmt.order_by(column.desc() if order == "desc" else column.asc())
        return list(self.session.scalars(stmt).all())

    def cities(self) -> list[str]:
        """Список городов гостей (для фильтра)."""
        rows = self.session.scalars(select(Guest.city).distinct().order_by(Guest.city)).all()
        return [row for row in rows if row]

    def count(self) -> int:
        """Общее количество гостей."""
        return int(self.session.scalar(select(func.count(Guest.id))) or 0)


class BookingRepository(BaseRepository):
    """Запросы по бронированиям."""

    model = Booking

    def get(self, booking_id: int) -> Booking | None:
        """Возвращает бронирование по идентификатору вместе со связями."""
        stmt = (
            select(Booking)
            .options(selectinload(Booking.room), selectinload(Booking.guest))
            .where(Booking.id == booking_id)
        )
        return self.session.scalar(stmt)

    def list(
        self,
        *,
        room_id: int | None = None,
        guest_id: int | None = None,
        status: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        search: str | None = None,
        sort: str = "check_in",
        order: str = "desc",
    ) -> Sequence[Booking]:
        """Возвращает бронирования с фильтрацией и сортировкой."""
        stmt: Select = select(Booking).options(
            selectinload(Booking.room), selectinload(Booking.guest)
        )
        if room_id is not None:
            stmt = stmt.where(Booking.room_id == room_id)
        if guest_id is not None:
            stmt = stmt.where(Booking.guest_id == guest_id)
        if status:
            stmt = stmt.where(Booking.status == status)
        if date_from is not None:
            stmt = stmt.where(Booking.check_out > date_from)
        if date_to is not None:
            stmt = stmt.where(Booking.check_in < date_to)
        if search:
            stmt = (
                stmt.join(Booking.guest)
                .join(Booking.room)
                .where(
                    self._search(
                        [Guest.full_name, Guest.email, Room.number, Booking.comment], search
                    )
                )
            )
        columns = {
            "check_in": Booking.check_in,
            "check_out": Booking.check_out,
            "price": Booking.total_price,
            "id": Booking.id,
        }
        column = columns.get(sort, Booking.check_in)
        stmt = stmt.order_by(column.desc() if order == "desc" else column.asc())
        return list(self.session.scalars(stmt).unique().all())

    def find_overlapping(
        self,
        room_id: int,
        check_in: date,
        check_out: date,
        *,
        exclude_id: int | None = None,
    ) -> list[Booking]:
        """Ищет подтверждённые бронирования, пересекающиеся по датам.

        Два интервала [a1; a2) и [b1; b2) пересекаются тогда и только тогда,
        когда a1 < b2 и b1 < a2. Именно это условие используется в запросе.
        """
        stmt = (
            select(Booking)
            .options(selectinload(Booking.room), selectinload(Booking.guest))
            .where(
                Booking.room_id == room_id,
                Booking.status == "confirmed",
                Booking.check_in < check_out,
                Booking.check_out > check_in,
            )
            .order_by(Booking.check_in)
        )
        if exclude_id is not None:
            stmt = stmt.where(Booking.id != exclude_id)
        return list(self.session.scalars(stmt).all())

    def count(self) -> int:
        """Общее количество бронирований."""
        return int(self.session.scalar(select(func.count(Booking.id))) or 0)

    def count_by_status(self, status: str) -> int:
        """Количество бронирований с указанным статусом."""
        stmt = select(func.count(Booking.id)).where(Booking.status == status)
        return int(self.session.scalar(stmt) or 0)

    def total_revenue(self) -> float:
        """Суммарная стоимость подтверждённых бронирований."""
        stmt = select(func.coalesce(func.sum(Booking.total_price), 0.0)).where(
            Booking.status == "confirmed"
        )
        return round(float(self.session.scalar(stmt) or 0.0), 2)
