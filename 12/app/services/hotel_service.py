"""Сервисный слой: бизнес-логика отеля и управление транзакциями."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.exceptions import (
    BookingConflictError,
    DuplicateError,
    HotelError,
    NotEnoughCapacityError,
    NotFoundError,
    RoomUnavailableError,
    TransactionError,
    ValidationError,
)
from app.models.booking import Booking, BookingStatus
from app.models.guest import Guest
from app.models.room import Room
from app.repositories.booking_repository import BookingRepository
from app.repositories.guest_repository import GuestRepository
from app.repositories.room_repository import RoomRepository

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class BookingResult:
    """Результат успешной транзакции бронирования."""

    booking: Booking
    guest: Guest
    room: Room
    nights: int
    total_price: Decimal

    def describe(self) -> str:
        """Человекочитаемое описание результата."""
        return (
            f"Бронь #{self.booking.id} оформлена: {self.guest.full_name} → "
            f"номер {self.room.number} ({self.room.room_type}), "
            f"{self.booking.check_in} → {self.booking.check_out}, "
            f"{self.nights} ноч., итого {self.total_price} руб."
        )


class HotelService:
    """Единая точка входа в бизнес-логику приложения «Отель».

    Сервис координирует репозитории и управляет транзакциями: успешные
    операции фиксируются (commit), при ошибке выполняется rollback и
    выбрасывается понятное доменное исключение.
    """

    def __init__(self, session: Session) -> None:
        self.session = session
        self.guests = GuestRepository(session)
        self.rooms = RoomRepository(session)
        self.bookings = BookingRepository(session)

    # ------------------------------------------------------------------ гости
    def register_guest(self, full_name: str, email: str, phone: str) -> Guest:
        """Зарегистрировать нового гостя (транзакция с commit)."""
        try:
            guest = self.guests.create(full_name, email, phone)
            self.session.commit()
        except HotelError:
            self.session.rollback()
            raise
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise TransactionError(f"Не удалось создать гостя: {exc}") from exc
        logger.info("Зарегистрирован гость id=%s email=%s", guest.id, guest.email)
        return guest

    def get_guest(self, guest_id: int) -> Guest:
        """Получить гостя по id.

        :raises NotFoundError: если гостя нет.
        """
        guest = self.guests.get_by_id(guest_id)
        if guest is None:
            raise NotFoundError(f"Гость с id={guest_id} не найден")
        return guest

    def list_guests(self) -> list[Guest]:
        """Список всех гостей."""
        return self.guests.list_sorted()

    def search_guests(self, full_name: str | None = None, phone: str | None = None, email: str | None = None) -> list[Guest]:
        """Поиск гостей по нескольким атрибутам."""
        return self.guests.search(full_name=full_name, phone=phone, email=email)

    def update_guest(self, guest_id: int, **fields: str) -> Guest:
        """Изменить данные гостя."""
        guest = self.get_guest(guest_id)
        try:
            self.guests.update_guest(guest, **fields)
            self.session.commit()
        except HotelError:
            self.session.rollback()
            raise
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise TransactionError(f"Не удалось изменить гостя: {exc}") from exc
        return guest

    def delete_guest(self, guest_id: int) -> None:
        """Удалить гостя вместе с его бронями (каскад ORM)."""
        guest = self.get_guest(guest_id)
        try:
            self.guests.delete(guest)
            self.session.commit()
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise TransactionError(f"Не удалось удалить гостя: {exc}") from exc

    # ----------------------------------------------------------------- номера
    def add_room(
        self,
        number: str,
        room_type: str,
        capacity: int,
        price_per_night: Decimal | float | str,
        is_active: bool = True,
    ) -> Room:
        """Добавить номер в отель."""
        try:
            room = self.rooms.create(number, room_type, capacity, price_per_night, is_active)
            self.session.commit()
        except HotelError:
            self.session.rollback()
            raise
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise TransactionError(f"Не удалось создать номер: {exc}") from exc
        logger.info("Добавлен номер id=%s number=%s", room.id, room.number)
        return room

    def get_room(self, room_id: int) -> Room:
        """Получить номер по id."""
        room = self.rooms.get_by_id(room_id)
        if room is None:
            raise NotFoundError(f"Номер с id={room_id} не найден")
        return room

    def list_rooms(self) -> list[Room]:
        """Список всех номеров (сортировка по цене)."""
        return self.rooms.list_sorted_by_price()

    def filter_rooms(
        self,
        room_type: str | None = None,
        min_capacity: int | None = None,
        is_active: bool | None = None,
        min_price: Decimal | float | None = None,
        max_price: Decimal | float | None = None,
    ) -> list[Room]:
        """Фильтрация номеров по нескольким критериям."""
        return self.rooms.search(
            room_type=room_type,
            min_capacity=min_capacity,
            is_active=is_active,
            min_price=min_price,
            max_price=max_price,
        )

    def available_rooms(self, check_in: date, check_out: date, min_capacity: int | None = None) -> list[Room]:
        """Свободные номера на интервал дат."""
        if check_out <= check_in:
            raise ValidationError("Дата выезда должна быть позже даты заезда")
        return self.rooms.find_available(check_in, check_out, min_capacity)

    def update_room(self, room_id: int, **fields: object) -> Room:
        """Изменить параметры номера."""
        room = self.get_room(room_id)
        try:
            self.rooms.update_room(room, **fields)  # type: ignore[arg-type]
            self.session.commit()
        except HotelError:
            self.session.rollback()
            raise
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise TransactionError(f"Не удалось изменить номер: {exc}") from exc
        return room

    def delete_room(self, room_id: int) -> None:
        """Удалить номер. Если на него ссылаются брони — сработает ограничение FK."""
        room = self.get_room(room_id)
        try:
            self.rooms.delete(room)
            self.session.commit()
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise TransactionError(
                f"Не удалось удалить номер {room.number}: есть связанные брони ({exc})"
            ) from exc

    # ----------------------------------------------------------- бронирование
    def book_room(
        self,
        guest_id: int,
        room_id: int,
        check_in: date,
        check_out: date,
        guests_count: int = 1,
    ) -> BookingResult:
        """Транзакционное бронирование номера.

        Шаги транзакции:
          1. валидация дат и количества гостей;
          2. проверка существования гостя и номера;
          3. проверка активности номера и вместимости;
          4. проверка пересечения дат с активными бронями;
          5. расчёт стоимости (ночи × цена) и вставка записи.

        При любой ошибке выполняется session.rollback(), а наружу
        выбрасывается соответствующее доменное исключение.
        """
        session = self.session
        try:
            if check_out <= check_in:
                raise ValidationError(
                    f"Некорректные даты: выезд {check_out} не позже заезда {check_in}"
                )
            if guests_count < 1:
                raise ValidationError("Количество гостей должно быть не меньше 1")

            guest = session.get(Guest, guest_id)
            if guest is None:
                raise NotFoundError(f"Гость с id={guest_id} не найден")
            room = session.get(Room, room_id)
            if room is None:
                raise NotFoundError(f"Номер с id={room_id} не найден")

            if not room.is_active:
                raise RoomUnavailableError(f"Номер {room.number} снят с продажи")

            if guests_count > room.capacity:
                raise NotEnoughCapacityError(
                    f"Номер {room.number} вмещает {room.capacity} гост(ей), запрошено {guests_count}"
                )

            conflicts = self.bookings.find_overlapping(room_id, check_in, check_out)
            if conflicts:
                busy = ", ".join(
                    f"#{b.id} ({b.check_in}—{b.check_out})" for b in conflicts
                )
                raise BookingConflictError(
                    f"Номер {room.number} занят на выбранные даты: {busy}"
                )

            nights = (check_out - check_in).days
            total_price = Decimal(room.price_per_night) * nights

            booking = self.bookings.create(
                guest_id=guest.id,
                room_id=room.id,
                check_in=check_in,
                check_out=check_out,
                total_price=total_price,
                status=BookingStatus.ACTIVE.value,
            )
            session.commit()
            logger.info(
                "Создана бронь id=%s гость=%s номер=%s %s..%s",
                booking.id, guest.id, room.number, check_in, check_out,
            )
            return BookingResult(
                booking=booking,
                guest=guest,
                room=room,
                nights=nights,
                total_price=total_price,
            )
        except HotelError:
            session.rollback()
            logger.warning("Транзакция бронирования отменена (rollback)")
            raise
        except SQLAlchemyError as exc:
            session.rollback()
            logger.error("Ошибка SQL при бронировании, выполнен rollback: %s", exc)
            raise TransactionError(f"Ошибка транзакции бронирования: {exc}") from exc

    def get_booking(self, booking_id: int) -> Booking:
        """Получить бронь по id."""
        booking = self.bookings.get_by_id(booking_id)
        if booking is None:
            raise NotFoundError(f"Бронь с id={booking_id} не найдена")
        return booking

    def cancel_booking(self, booking_id: int) -> Booking:
        """Отменить бронь (сменить статус на cancelled)."""
        booking = self.get_booking(booking_id)
        try:
            self.bookings.update_booking(booking, status=BookingStatus.CANCELLED.value)
            self.session.commit()
        except HotelError:
            self.session.rollback()
            raise
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise TransactionError(f"Не удалось отменить бронь: {exc}") from exc
        return booking

    def change_booking_status(self, booking_id: int, status: str) -> Booking:
        """Изменить статус брони с проверкой допустимых значений."""
        allowed = {s.value for s in BookingStatus}
        if status not in allowed:
            raise ValidationError(
                f"Недопустимый статус {status!r}; допустимы: {', '.join(sorted(allowed))}"
            )
        booking = self.get_booking(booking_id)
        try:
            self.bookings.update_booking(booking, status=status)
            self.session.commit()
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise TransactionError(f"Не удалось изменить статус: {exc}") from exc
        return booking

    def reschedule_booking(self, booking_id: int, check_in: date, check_out: date) -> Booking:
        """Перенести бронь на новые даты с проверкой пересечений (транзакция)."""
        session = self.session
        try:
            booking = session.get(Booking, booking_id)
            if booking is None:
                raise NotFoundError(f"Бронь с id={booking_id} не найдена")
            if check_out <= check_in:
                raise ValidationError("Дата выезда должна быть позже даты заезда")
            conflicts = self.bookings.find_overlapping(
                booking.room_id, check_in, check_out, exclude_booking_id=booking.id
            )
            if conflicts:
                raise BookingConflictError(
                    f"Новые даты пересекаются с бронями: "
                    + ", ".join(f"#{b.id}" for b in conflicts)
                )
            nights = (check_out - check_in).days
            price = Decimal(booking.room.price_per_night) * nights
            self.bookings.update_booking(
                booking, check_in=check_in, check_out=check_out, total_price=price
            )
            session.commit()
            return booking
        except HotelError:
            session.rollback()
            raise
        except SQLAlchemyError as exc:
            session.rollback()
            raise TransactionError(f"Не удалось перенести бронь: {exc}") from exc

    def delete_booking(self, booking_id: int) -> None:
        """Удалить бронь."""
        booking = self.get_booking(booking_id)
        try:
            self.bookings.delete(booking)
            self.session.commit()
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise TransactionError(f"Не удалось удалить бронь: {exc}") from exc

    # ------------------------------------------------------ связанные выборки
    def bookings_of_guest(self, guest_id: int) -> list[Booking]:
        """Все брони гостя (получение связанных объектов)."""
        self.get_guest(guest_id)
        return self.bookings.list_by_guest(guest_id)

    def bookings_of_room(self, room_id: int) -> list[Booking]:
        """Все брони номера."""
        self.get_room(room_id)
        return self.bookings.list_by_room(room_id)

    def filter_bookings(
        self,
        status: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        min_price: Decimal | float | None = None,
        max_price: Decimal | float | None = None,
    ) -> list[Booking]:
        """Фильтрация броней по статусу/датам/стоимости."""
        return self.bookings.list_filtered(status, date_from, date_to, min_price, max_price)

    def rooms_sorted_by_price(self, descending: bool = False) -> list[Room]:
        """Сортировка номеров по цене."""
        return self.rooms.list_sorted_by_price(descending)

    def rooms_sorted_by_capacity(self, descending: bool = True) -> list[Room]:
        """Сортировка номеров по вместимости."""
        return self.rooms.list_sorted_by_capacity(descending)

    def bookings_sorted_by_check_in(self, descending: bool = False) -> list[Booking]:
        """Сортировка броней по дате заезда."""
        return self.bookings.list_sorted_by_check_in(descending)

    def bookings_sorted_by_total(self, descending: bool = True) -> list[Booking]:
        """Сортировка броней по итоговой стоимости."""
        return self.bookings.list_sorted_by_total_price(descending)
