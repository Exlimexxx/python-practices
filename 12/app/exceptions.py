"""Собственная иерархия исключений приложения «Отель»."""
from __future__ import annotations


class HotelError(Exception):
    """Базовое исключение предметной области."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    def __str__(self) -> str:
        return self.message


class ValidationError(HotelError):
    """Некорректные входные данные (пустые поля, неверные даты и т. п.)."""


class NotFoundError(HotelError):
    """Запрошенный объект не найден в базе данных."""


class DuplicateError(HotelError):
    """Нарушено ограничение уникальности (email гостя, номер комнаты)."""


class NotEnoughCapacityError(HotelError):
    """Количество гостей превышает вместимость номера."""


class RoomUnavailableError(HotelError):
    """Номер неактивен или занят на выбранные даты."""


class BookingConflictError(RoomUnavailableError):
    """Даты бронирования пересекаются с существующей бронью."""


class TransactionError(HotelError):
    """Ошибка выполнения транзакции (откат выполнен)."""
