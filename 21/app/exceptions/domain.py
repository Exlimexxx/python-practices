"""Иерархия исключений предметной области.

Каждое исключение несёт код ошибки для API и HTTP-статус, поэтому обработчики
FastAPI лишь сопоставляют исключение с ответом, не разбирая типы вручную.
"""
from __future__ import annotations


class AppError(Exception):
    """Базовое исключение приложения."""

    code = "APPLICATION_ERROR"
    status_code = 500

    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict:
        payload: dict = {"error": self.code, "message": self.message}
        if self.details:
            payload["details"] = self.details
        return payload


class ValidationFailure(AppError):
    """Некорректные данные, не прошедшие бизнес-проверку."""

    code = "VALIDATION_ERROR"
    status_code = 422


class EntityNotFoundError(AppError):
    """Запрошенная сущность отсутствует."""

    code = "ENTITY_NOT_FOUND"
    status_code = 404


class UserNotFoundError(EntityNotFoundError):
    code = "USER_NOT_FOUND"


class RoomNotFoundError(EntityNotFoundError):
    code = "ROOM_NOT_FOUND"


class BookingNotFoundError(EntityNotFoundError):
    code = "BOOKING_NOT_FOUND"


class PaymentNotFoundError(EntityNotFoundError):
    code = "PAYMENT_NOT_FOUND"


class BusinessRuleError(AppError):
    """Нарушено правило предметной области."""

    code = "BUSINESS_RULE_VIOLATION"
    status_code = 409


class EmailAlreadyUsedError(BusinessRuleError):
    code = "EMAIL_ALREADY_USED"


class RoomNumberAlreadyUsedError(BusinessRuleError):
    code = "ROOM_NUMBER_ALREADY_USED"


class RoomNotAvailableError(BusinessRuleError):
    code = "ROOM_NOT_AVAILABLE"


class RoomHasBookingsError(BusinessRuleError):
    code = "ROOM_HAS_BOOKINGS"


class BookingOverlapError(BusinessRuleError):
    code = "BOOKING_OVERLAP"


class BookingStatusError(BusinessRuleError):
    code = "BOOKING_STATUS_INVALID"


class BookingNotPaidError(BusinessRuleError):
    code = "BOOKING_NOT_PAID"


class PaymentAmountError(BusinessRuleError):
    code = "PAYMENT_AMOUNT_EXCEEDED"


class AuthenticationError(AppError):
    code = "AUTHENTICATION_FAILED"
    status_code = 401


class PermissionDeniedError(AppError):
    code = "PERMISSION_DENIED"
    status_code = 403


class ExternalServiceError(AppError):
    """Внешняя зависимость недоступна."""

    code = "EXTERNAL_SERVICE_UNAVAILABLE"
    status_code = 503
