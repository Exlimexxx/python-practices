"""Собственные исключения приложения (вариант 4 «Отель»)."""
from __future__ import annotations


class HotelError(Exception):
    """Базовое исключение предметной области отеля."""

    status_code: int = 500
    default_message: str = "Непредвиденная ошибка приложения"

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.default_message
        super().__init__(self.message)

    def to_dict(self) -> dict[str, object]:
        """Представление исключения для JSON-ответа REST API."""
        return {
            "error": type(self).__name__,
            "message": self.message,
            "status": self.status_code,
        }


class ValidationError(HotelError):
    """Некорректные входные данные (HTTP 400)."""

    status_code = 400
    default_message = "Некорректные данные запроса"


class NotFoundError(HotelError):
    """Запрашиваемый объект не найден (HTTP 404)."""

    status_code = 404
    default_message = "Объект не найден"


class ConflictError(HotelError):
    """Конфликт данных, например нарушение уникальности (HTTP 409)."""

    status_code = 409
    default_message = "Конфликт данных"


class BookingConflictError(ConflictError):
    """Попытка забронировать номер на занятые даты (HTTP 409)."""

    status_code = 409
    default_message = "Номер уже забронирован на выбранные даты"

    def __init__(
        self,
        message: str | None = None,
        *,
        room_id: int | None = None,
        check_in: str | None = None,
        check_out: str | None = None,
        conflicts: list[dict[str, object]] | None = None,
    ) -> None:
        super().__init__(message)
        self.room_id = room_id
        self.check_in = check_in
        self.check_out = check_out
        self.conflicts = conflicts or []

    def to_dict(self) -> dict[str, object]:
        data = super().to_dict()
        data.update(
            {
                "room_id": self.room_id,
                "check_in": self.check_in,
                "check_out": self.check_out,
                "conflicts": self.conflicts,
            }
        )
        return data


class RoomCapacityError(ValidationError):
    """Число гостей превышает вместимость номера (HTTP 400)."""

    default_message = "Количество гостей превышает вместимость номера"


class PersistenceError(HotelError):
    """Ошибка при работе с базой данных (HTTP 500)."""

    status_code = 500
    default_message = "Ошибка при сохранении данных"
