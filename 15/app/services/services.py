"""Сервисный слой: валидация данных и бизнес-логика бронирования.

Здесь сосредоточено правило пересечения дат и расчёт стоимости проживания.
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any, Mapping

from sqlalchemy.orm import Session

from app.exceptions import (
    BookingConflictError,
    NotFoundError,
    RoomCapacityError,
    ValidationError,
)
from app.models import BOOKING_STATUSES, ROOM_TYPES, Booking, Guest, Room
from app.repositories import BookingRepository, GuestRepository, RoomRepository

logger = logging.getLogger(__name__)

#: Максимально допустимая длительность бронирования, ночей.
MAX_NIGHTS = 365
#: Максимальная вместимость номера, человек.
MAX_CAPACITY = 20


def _clean_str(value: Any, *, field: str, required: bool = True, max_length: int = 255) -> str:
    """Приводит значение к строке и проверяет обязательность/длину."""
    if value is None or (isinstance(value, str) and not value.strip()):
        if required:
            raise ValidationError(f"Поле «{field}» обязательно для заполнения")
        return ""
    text = str(value).strip()
    if len(text) > max_length:
        raise ValidationError(f"Поле «{field}» не должно превышать {max_length} символов")
    return text


def _to_int(value: Any, *, field: str, default: int | None = None, minimum: int | None = None,
            maximum: int | None = None) -> int:
    """Приводит значение к целому числу с проверкой границ."""
    if value is None or (isinstance(value, str) and not value.strip()):
        if default is None:
            raise ValidationError(f"Поле «{field}» обязательно для заполнения")
        result = default
    else:
        try:
            result = int(str(value).strip())
        except (TypeError, ValueError) as exc:
            raise ValidationError(f"Поле «{field}» должно быть целым числом") from exc
    if minimum is not None and result < minimum:
        raise ValidationError(f"Поле «{field}» не может быть меньше {minimum}")
    if maximum is not None and result > maximum:
        raise ValidationError(f"Поле «{field}» не может быть больше {maximum}")
    return result


def _to_float(value: Any, *, field: str, default: float | None = None, minimum: float | None = None) -> float:
    """Приводит значение к числу с плавающей точкой."""
    if value is None or (isinstance(value, str) and not value.strip()):
        if default is None:
            raise ValidationError(f"Поле «{field}» обязательно для заполнения")
        result = default
    else:
        try:
            result = float(str(value).replace(",", ".").strip())
        except (TypeError, ValueError) as exc:
            raise ValidationError(f"Поле «{field}» должно быть числом") from exc
    if minimum is not None and result < minimum:
        raise ValidationError(f"Поле «{field}» не может быть меньше {minimum}")
    return round(result, 2)


def _to_bool(value: Any, *, default: bool = False) -> bool:
    """Интерпретирует значение как логическое."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on", "да"}


def _to_date(value: Any, *, field: str) -> date:
    """Разбирает дату в формате ISO (YYYY-MM-DD)."""
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if value is None or not str(value).strip():
        raise ValidationError(f"Поле «{field}» обязательно для заполнения")
    try:
        return date.fromisoformat(str(value).strip()[:10])
    except ValueError as exc:
        raise ValidationError(f"Поле «{field}» должно быть датой в формате ГГГГ-ММ-ДД") from exc


class RoomService:
    """Операции над номерами."""

    def __init__(self, session: Session) -> None:
        self.repo = RoomRepository(session)

    def get(self, room_id: int) -> Room:
        """Возвращает номер или возбуждает NotFoundError."""
        room = self.repo.get(room_id)
        if room is None:
            raise NotFoundError(f"Номер с идентификатором {room_id} не найден")
        return room

    def list(self, **filters: Any) -> list[Room]:
        """Список номеров по фильтрам."""
        return list(self.repo.list(**filters))

    def create(self, data: Mapping[str, Any]) -> Room:
        """Создаёт номер после валидации полей."""
        room_type = _clean_str(data.get("room_type"), field="Тип номера", max_length=40)
        if room_type not in ROOM_TYPES:
            raise ValidationError(
                "Тип номера должен быть одним из: " + ", ".join(ROOM_TYPES)
            )
        room = Room(
            number=_clean_str(data.get("number"), field="Номер", max_length=10),
            room_type=room_type,
            capacity=_to_int(data.get("capacity"), field="Вместимость", default=2,
                             minimum=1, maximum=MAX_CAPACITY),
            price_per_night=_to_float(data.get("price_per_night"), field="Цена за ночь",
                                      default=0.0, minimum=0.0),
            floor=_to_int(data.get("floor"), field="Этаж", default=1, minimum=1, maximum=100),
            description=_clean_str(data.get("description"), field="Описание", required=False,
                                   max_length=2000),
            is_active=_to_bool(data.get("is_active"), default=True),
        )
        if self.repo.get_by_number(room.number) is not None:
            raise ValidationError(f"Номер «{room.number}» уже существует")
        created = self.repo.add(room)
        logger.info("Создан номер id=%s number=%s", created.id, created.number)
        return created

    def update(self, room_id: int, data: Mapping[str, Any]) -> Room:
        """Обновляет номер."""
        room = self.get(room_id)
        if "number" in data:
            number = _clean_str(data.get("number"), field="Номер", max_length=10)
            existing = self.repo.get_by_number(number)
            if existing is not None and existing.id != room.id:
                raise ValidationError(f"Номер «{number}» уже существует")
            room.number = number
        if "room_type" in data:
            room_type = _clean_str(data.get("room_type"), field="Тип номера", max_length=40)
            if room_type not in ROOM_TYPES:
                raise ValidationError("Тип номера должен быть одним из: " + ", ".join(ROOM_TYPES))
            room.room_type = room_type
        if "capacity" in data:
            room.capacity = _to_int(data.get("capacity"), field="Вместимость", default=room.capacity,
                                    minimum=1, maximum=MAX_CAPACITY)
        if "price_per_night" in data:
            room.price_per_night = _to_float(data.get("price_per_night"), field="Цена за ночь",
                                             default=room.price_per_night, minimum=0.0)
        if "floor" in data:
            room.floor = _to_int(data.get("floor"), field="Этаж", default=room.floor,
                                 minimum=1, maximum=100)
        if "description" in data:
            room.description = _clean_str(data.get("description"), field="Описание",
                                          required=False, max_length=2000)
        if "is_active" in data:
            room.is_active = _to_bool(data.get("is_active"), default=room.is_active)
        updated = self.repo.add(room)
        logger.info("Обновлён номер id=%s", updated.id)
        return updated

    def delete(self, room_id: int) -> None:
        """Удаляет номер вместе со связанными бронированиями (cascade)."""
        room = self.get(room_id)
        self.repo.delete(room)
        logger.warning("Удалён номер id=%s number=%s", room_id, room.number)

    @staticmethod
    def room_types() -> tuple[str, ...]:
        """Справочник типов номеров."""
        return ROOM_TYPES


class GuestService:
    """Операции над гостями."""

    def __init__(self, session: Session) -> None:
        self.repo = GuestRepository(session)

    def get(self, guest_id: int) -> Guest:
        """Возвращает гостя или возбуждает NotFoundError."""
        guest = self.repo.get(guest_id)
        if guest is None:
            raise NotFoundError(f"Гость с идентификатором {guest_id} не найден")
        return guest

    def list(self, **filters: Any) -> list[Guest]:
        """Список гостей по фильтрам."""
        return list(self.repo.list(**filters))

    def create(self, data: Mapping[str, Any]) -> Guest:
        """Создаёт гостя после валидации полей."""
        email = _clean_str(data.get("email"), field="Email", max_length=120).lower()
        if "@" not in email or "." not in email.split("@")[-1]:
            raise ValidationError("Email указан в некорректном формате")
        guest = Guest(
            full_name=_clean_str(data.get("full_name"), field="ФИО", max_length=120),
            email=email,
            phone=_clean_str(data.get("phone"), field="Телефон", required=False, max_length=30),
            passport=_clean_str(data.get("passport"), field="Паспорт", required=False, max_length=20),
            city=_clean_str(data.get("city"), field="Город", required=False, max_length=80),
        )
        if self.repo.get_by_email(email) is not None:
            raise ValidationError(f"Гость с email «{email}» уже существует")
        created = self.repo.add(guest)
        logger.info("Создан гость id=%s email=%s", created.id, created.email)
        return created

    def update(self, guest_id: int, data: Mapping[str, Any]) -> Guest:
        """Обновляет данные гостя."""
        guest = self.get(guest_id)
        if "full_name" in data:
            guest.full_name = _clean_str(data.get("full_name"), field="ФИО", max_length=120)
        if "email" in data:
            email = _clean_str(data.get("email"), field="Email", max_length=120).lower()
            if "@" not in email or "." not in email.split("@")[-1]:
                raise ValidationError("Email указан в некорректном формате")
            existing = self.repo.get_by_email(email)
            if existing is not None and existing.id != guest.id:
                raise ValidationError(f"Гость с email «{email}» уже существует")
            guest.email = email
        if "phone" in data:
            guest.phone = _clean_str(data.get("phone"), field="Телефон", required=False, max_length=30)
        if "passport" in data:
            guest.passport = _clean_str(data.get("passport"), field="Паспорт", required=False, max_length=20)
        if "city" in data:
            guest.city = _clean_str(data.get("city"), field="Город", required=False, max_length=80)
        updated = self.repo.add(guest)
        logger.info("Обновлён гость id=%s", updated.id)
        return updated

    def delete(self, guest_id: int) -> None:
        """Удаляет гостя вместе с его бронированиями."""
        guest = self.get(guest_id)
        self.repo.delete(guest)
        logger.warning("Удалён гость id=%s email=%s", guest_id, guest.email)


class BookingService:
    """Операции над бронированиями и правило пересечения дат."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = BookingRepository(session)
        self.rooms = RoomRepository(session)
        self.guests = GuestRepository(session)

    def get(self, booking_id: int) -> Booking:
        """Возвращает бронирование или возбуждает NotFoundError."""
        booking = self.repo.get(booking_id)
        if booking is None:
            raise NotFoundError(f"Бронирование с идентификатором {booking_id} не найдено")
        return booking

    def list(self, **filters: Any) -> list[Booking]:
        """Список бронирований по фильтрам."""
        return list(self.repo.list(**filters))

    def _resolve_room(self, room_id: int) -> Room:
        """Находит номер и проверяет, что он доступен для бронирования."""
        room = self.rooms.get(room_id)
        if room is None:
            raise NotFoundError(f"Номер с идентификатором {room_id} не найден")
        if not room.is_active:
            raise ValidationError(f"Номер «{room.number}» закрыт для бронирования")
        return room

    def _resolve_guest(self, guest_id: int) -> Guest:
        """Находит гостя по идентификатору."""
        guest = self.guests.get(guest_id)
        if guest is None:
            raise NotFoundError(f"Гость с идентификатором {guest_id} не найден")
        return guest

    @staticmethod
    def calculate_price(room: Room, check_in: date, check_out: date) -> float:
        """Считает стоимость проживания: число ночей * цена за ночь."""
        nights = (check_out - check_in).days
        return round(nights * room.price_per_night, 2)

    def check_overlap(
        self, room_id: int, check_in: date, check_out: date, *, exclude_id: int | None = None
    ) -> None:
        """Проверяет пересечение с существующими бронированиями.

        При пересечении возбуждает BookingConflictError (HTTP 409).
        """
        conflicts = self.repo.find_overlapping(room_id, check_in, check_out, exclude_id=exclude_id)
        if conflicts:
            logger.warning(
                "Конфликт бронирования: номер=%s даты=%s..%s пересекаются с %s",
                room_id, check_in, check_out, [b.id for b in conflicts],
            )
            payload = [b.to_dict(with_relations=False) for b in conflicts]
            raise BookingConflictError(
                "Номер уже забронирован на пересекающиеся даты",
                room_id=room_id,
                check_in=check_in.isoformat(),
                check_out=check_out.isoformat(),
                conflicts=payload,
            )

    def availability(
        self, room_id: int, check_in: date, check_out: date, *, exclude_id: int | None = None
    ) -> tuple[bool, list[dict[str, Any]]]:
        """Проверка доступности без возбуждения исключения (для AJAX/API)."""
        conflicts = self.repo.find_overlapping(room_id, check_in, check_out, exclude_id=exclude_id)
        return (not conflicts, [b.to_dict(with_relations=False) for b in conflicts])

    def _prepare_dates(
        self, data: Mapping[str, Any]
    ) -> tuple[date, date]:
        """Разбирает и валидирует даты заезда/выезда."""
        check_in = _to_date(data.get("check_in"), field="Дата заезда")
        check_out = _to_date(data.get("check_out"), field="Дата выезда")
        if check_out <= check_in:
            raise ValidationError("Дата выезда должна быть позже даты заезда")
        nights = (check_out - check_in).days
        if nights > MAX_NIGHTS:
            raise ValidationError(f"Длительность бронирования не может превышать {MAX_NIGHTS} ночей")
        return check_in, check_out

    def create(self, data: Mapping[str, Any]) -> Booking:
        """Создаёт бронирование с проверкой пересечения и расчётом стоимости."""
        room_id = _to_int(data.get("room_id"), field="Номер")
        guest_id = _to_int(data.get("guest_id"), field="Гость")
        check_in, check_out = self._prepare_dates(data)
        room = self._resolve_room(room_id)
        guest = self._resolve_guest(guest_id)
        guests_count = _to_int(
            data.get("guests_count"), field="Количество гостей", default=1, minimum=1
        )
        if guests_count > room.capacity:
            raise RoomCapacityError(
                f"Номер «{room.number}» вмещает не более {room.capacity} гостей"
            )
        status = _clean_str(data.get("status", "confirmed"), field="Статус", required=False,
                            max_length=20) or "confirmed"
        if status not in BOOKING_STATUSES:
            raise ValidationError("Статус должен быть confirmed или cancelled")
        if status == "confirmed":
            self.check_overlap(room_id, check_in, check_out)
        booking = Booking(
            room_id=room_id,
            guest_id=guest_id,
            check_in=check_in,
            check_out=check_out,
            guests_count=guests_count,
            status=status,
            total_price=self.calculate_price(room, check_in, check_out),
            comment=_clean_str(data.get("comment"), field="Комментарий", required=False,
                               max_length=1000),
        )
        created = self.repo.add(booking)
        logger.info(
            "Создано бронирование id=%s номер=%s гость=%s %s..%s стоимость=%.2f",
            created.id, room_id, guest_id, check_in, check_out, created.total_price,
        )
        return created

    def update(self, booking_id: int, data: Mapping[str, Any]) -> Booking:
        """Изменяет бронирование, повторно проверяя пересечение дат."""
        booking = self.get(booking_id)
        room_id = booking.room_id
        guest_id = booking.guest_id
        if "room_id" in data:
            room_id = _to_int(data.get("room_id"), field="Номер")
        if "guest_id" in data:
            guest_id = _to_int(data.get("guest_id"), field="Гость")
        check_in = booking.check_in
        check_out = booking.check_out
        if "check_in" in data or "check_out" in data:
            merged = {
                "check_in": data.get("check_in", booking.check_in),
                "check_out": data.get("check_out", booking.check_out),
            }
            check_in, check_out = self._prepare_dates(merged)
        room = self._resolve_room(room_id)
        self._resolve_guest(guest_id)
        guests_count = booking.guests_count
        if "guests_count" in data:
            guests_count = _to_int(data.get("guests_count"), field="Количество гостей",
                                   default=booking.guests_count, minimum=1)
        if guests_count > room.capacity:
            raise RoomCapacityError(f"Номер «{room.number}» вмещает не более {room.capacity} гостей")
        status = booking.status
        if "status" in data:
            status = _clean_str(data.get("status"), field="Статус", max_length=20)
            if status not in BOOKING_STATUSES:
                raise ValidationError("Статус должен быть confirmed или cancelled")
        # Пересечение проверяется, только если бронь остаётся подтверждённой.
        if status == "confirmed":
            self.check_overlap(room_id, check_in, check_out, exclude_id=booking.id)
        booking.room_id = room_id
        booking.guest_id = guest_id
        booking.check_in = check_in
        booking.check_out = check_out
        booking.guests_count = guests_count
        booking.status = status
        booking.comment = _clean_str(
            data.get("comment", booking.comment), field="Комментарий", required=False, max_length=1000
        )
        booking.total_price = self.calculate_price(room, check_in, check_out)
        updated = self.repo.add(booking)
        logger.info("Обновлено бронирование id=%s статус=%s", updated.id, updated.status)
        return updated

    def cancel(self, booking_id: int) -> Booking:
        """Отменяет бронирование."""
        booking = self.get(booking_id)
        booking.status = "cancelled"
        updated = self.repo.add(booking)
        logger.warning("Отменено бронирование id=%s", booking_id)
        return updated

    def delete(self, booking_id: int) -> None:
        """Удаляет бронирование."""
        booking = self.get(booking_id)
        self.repo.delete(booking)
        logger.warning("Удалено бронирование id=%s", booking_id)

    def statistics(self) -> dict[str, Any]:
        """Сводная статистика для главной страницы."""
        return {
            "rooms_total": self.rooms.count(),
            "rooms_active": self.rooms.count_active(),
            "guests_total": self.guests.count(),
            "bookings_total": self.repo.count(),
            "bookings_confirmed": self.repo.count_by_status("confirmed"),
            "bookings_cancelled": self.repo.count_by_status("cancelled"),
            "revenue": self.repo.total_revenue(),
        }
