"""Сервис гостиничных номеров."""
from __future__ import annotations

import logging
from datetime import date

from sqlalchemy.orm import Session

from app.exceptions import (
    RoomHasBookingsError,
    RoomNotFoundError,
    RoomNumberAlreadyUsedError,
    ValidationFailure,
)
from app.models import Room, RoomStatus, RoomType
from app.repositories.booking_repository import BookingRepository
from app.repositories.room_repository import RoomRepository
from app.schemas.room import RoomCreate, RoomFilter, RoomOut, RoomPage, RoomUpdate

logger = logging.getLogger(__name__)


def to_room_out(room: Room) -> RoomOut:
    return RoomOut(
        id=room.id,
        number=room.number,
        room_type=room.room_type,
        capacity=room.capacity,
        price_per_night=room.price_per_night,
        floor=room.floor,
        status=room.status,
        description=room.description,
        created_at=room.created_at,
    )


class RoomService:
    """Управление номерным фондом."""

    def __init__(
        self,
        session: Session,
        rooms: RoomRepository,
        bookings: BookingRepository | None = None,
    ) -> None:
        self.session = session
        self.rooms = rooms
        self.bookings = bookings

    def create_room(self, payload: RoomCreate) -> RoomOut:
        number = payload.number.strip().upper()
        if self.rooms.get_by_number(number) is not None:
            raise RoomNumberAlreadyUsedError(
                f"Номер {number} уже существует в каталоге", details={"number": number}
            )
        room = Room(
            number=number,
            room_type=payload.room_type,
            capacity=payload.capacity,
            price_per_night=round(payload.price_per_night, 2),
            floor=payload.floor,
            status=payload.status,
            description=payload.description,
        )
        self.rooms.add(room)
        self.session.commit()
        logger.info("Добавлен номер id=%s number=%s", room.id, room.number)
        return to_room_out(room)

    def get_entity(self, room_id: int) -> Room:
        room = self.rooms.get(room_id)
        if room is None:
            raise RoomNotFoundError(
                f"Номер с идентификатором {room_id} не найден", details={"room_id": room_id}
            )
        return room

    def get_room(self, room_id: int) -> RoomOut:
        return to_room_out(self.get_entity(room_id))

    def update_room(self, room_id: int, payload: RoomUpdate) -> RoomOut:
        room = self.get_entity(room_id)
        changes = payload.model_dump(exclude_unset=True)
        if not changes:
            raise ValidationFailure("Не передано ни одного поля для обновления")
        for field, value in changes.items():
            setattr(room, field, round(value, 2) if field == "price_per_night" else value)
        self.session.commit()
        logger.info("Обновлён номер id=%s fields=%s", room.id, sorted(changes))
        return to_room_out(room)

    def change_status(self, room_id: int, status: RoomStatus) -> RoomOut:
        room = self.get_entity(room_id)
        room.status = status
        self.session.commit()
        logger.info("Изменён статус номера id=%s status=%s", room.id, status.value)
        return to_room_out(room)

    def delete_room(self, room_id: int) -> None:
        room = self.get_entity(room_id)
        if self.rooms.has_active_bookings(room.id):
            raise RoomHasBookingsError(
                f"Номер {room.number} нельзя удалить: есть активные бронирования",
                details={"room_id": room.id},
            )
        self.rooms.delete(room)
        self.session.commit()
        logger.info("Удалён номер id=%s", room_id)

    def search_rooms(self, filters: RoomFilter) -> RoomPage:
        items, total = self.rooms.search(filters)
        return RoomPage(
            total=total,
            limit=filters.limit,
            offset=filters.offset,
            items=[to_room_out(room) for room in items],
        )

    def available_rooms(
        self,
        check_in: date,
        check_out: date,
        *,
        min_capacity: int | None = None,
        room_type: RoomType | None = None,
    ) -> list[RoomOut]:
        """Свободные номера на период: проверка пересечений с бронированиями."""
        if check_out <= check_in:
            raise ValidationFailure("Дата выезда должна быть позже даты заезда")
        rooms = self.rooms.available_between(
            check_in, check_out, min_capacity=min_capacity, room_type=room_type
        )
        return [to_room_out(room) for room in rooms]
