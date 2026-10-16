"""Репозиторий номеров: CRUD, фильтрация, поиск свободных номеров, сортировки."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions import DuplicateError, ValidationError
from app.models.booking import Booking, BookingStatus
from app.models.room import Room
from app.repositories.base import BaseRepository


class RoomRepository(BaseRepository[Room]):
    """Операции доступа к данным таблицы rooms."""

    model = Room

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def create(
        self,
        number: str,
        room_type: str,
        capacity: int,
        price_per_night: Decimal | float | str,
        is_active: bool = True,
    ) -> Room:
        """Создать номер с валидацией данных и контролем уникальности номера.

        :raises ValidationError: при некорректных значениях.
        :raises DuplicateError: если номер комнаты уже существует.
        """
        number = (number or "").strip()
        room_type = (room_type or "").strip()
        if not number:
            raise ValidationError("Номер комнаты не может быть пустым")
        if not room_type:
            raise ValidationError("Тип номера не может быть пустым")
        try:
            capacity = int(capacity)
        except (TypeError, ValueError) as exc:
            raise ValidationError("Вместимость должна быть целым числом") from exc
        if capacity <= 0:
            raise ValidationError("Вместимость должна быть положительной")
        try:
            price = Decimal(str(price_per_night))
        except Exception as exc:  # noqa: BLE001 - любая ошибка преобразования
            raise ValidationError("Цена должна быть числом") from exc
        if price < 0:
            raise ValidationError("Цена не может быть отрицательной")

        room = Room(
            number=number,
            room_type=room_type,
            capacity=capacity,
            price_per_night=price,
            is_active=bool(is_active),
        )
        self.session.add(room)
        try:
            self.session.flush()
        except IntegrityError as exc:
            self.session.rollback()
            raise DuplicateError("Номер " + repr(number) + " уже существует") from exc
        return room

    def get_by_number(self, number: str) -> Room | None:
        """Найти номер по его строковому обозначению."""
        return self.session.scalar(select(Room).where(Room.number == (number or "").strip()))

    def search(
        self,
        room_type: str | None = None,
        min_capacity: int | None = None,
        is_active: bool | None = None,
        min_price: Decimal | float | None = None,
        max_price: Decimal | float | None = None,
    ) -> list[Room]:
        """Фильтрация по нескольким условиям одновременно (AND)."""
        stmt = select(Room)
        conditions = []
        if room_type:
            conditions.append(Room.room_type.ilike("%" + room_type.strip() + "%"))
        if min_capacity is not None:
            conditions.append(Room.capacity >= int(min_capacity))
        if is_active is not None:
            conditions.append(Room.is_active.is_(bool(is_active)))
        if min_price is not None:
            conditions.append(Room.price_per_night >= Decimal(str(min_price)))
        if max_price is not None:
            conditions.append(Room.price_per_night <= Decimal(str(max_price)))
        if conditions:
            stmt = stmt.where(*conditions)
        return list(self.session.scalars(stmt.order_by(Room.number)).all())

    def find_available(
        self,
        check_in: date,
        check_out: date,
        min_capacity: int | None = None,
    ) -> list[Room]:
        """Свободные активные номера на заданный интервал дат.

        Подзапрос выбирает номера, у которых есть активная бронь,
        пересекающаяся с интервалом [check_in; check_out).
        """
        busy = select(Booking.room_id).where(
            Booking.status == BookingStatus.ACTIVE.value,
            Booking.check_in < check_out,
            Booking.check_out > check_in,
        )
        stmt = select(Room).where(Room.is_active.is_(True), Room.id.not_in(busy))
        if min_capacity is not None:
            stmt = stmt.where(Room.capacity >= int(min_capacity))
        return list(self.session.scalars(stmt.order_by(Room.price_per_night)).all())

    def list_sorted_by_price(self, descending: bool = False) -> list[Room]:
        """Сортировка №1: по цене за ночь."""
        order = Room.price_per_night.desc() if descending else Room.price_per_night.asc()
        return list(self.session.scalars(select(Room).order_by(order, Room.number)).all())

    def list_sorted_by_capacity(self, descending: bool = True) -> list[Room]:
        """Сортировка №2: по вместимости (числу мест)."""
        order = Room.capacity.desc() if descending else Room.capacity.asc()
        return list(self.session.scalars(select(Room).order_by(order, Room.number)).all())

    def update_room(
        self,
        room: Room,
        number: str | None = None,
        room_type: str | None = None,
        capacity: int | None = None,
        price_per_night: Decimal | float | None = None,
        is_active: bool | None = None,
    ) -> Room:
        """Изменить параметры номера."""
        payload: dict[str, object] = {}
        if number is not None:
            payload["number"] = number.strip()
        if room_type is not None:
            payload["room_type"] = room_type.strip()
        if capacity is not None:
            capacity = int(capacity)
            if capacity <= 0:
                raise ValidationError("Вместимость должна быть положительной")
            payload["capacity"] = capacity
        if price_per_night is not None:
            price = Decimal(str(price_per_night))
            if price < 0:
                raise ValidationError("Цена не может быть отрицательной")
            payload["price_per_night"] = price
        if is_active is not None:
            payload["is_active"] = bool(is_active)
        try:
            self.update(room, **payload)
        except IntegrityError as exc:
            self.session.rollback()
            raise DuplicateError("Не удалось изменить номер: номер комнаты уже занят") from exc
        return room
