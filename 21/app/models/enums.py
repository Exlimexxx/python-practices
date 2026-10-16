"""Перечисления предметной области: роли, типы номеров, статусы."""
from __future__ import annotations

from enum import Enum


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


class RoomType(str, Enum):
    STANDARD = "standard"
    COMFORT = "comfort"
    LUX = "lux"
    FAMILY = "family"


class RoomStatus(str, Enum):
    AVAILABLE = "available"
    MAINTENANCE = "maintenance"
    INACTIVE = "inactive"


class BookingStatus(str, Enum):
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class PaymentMethod(str, Enum):
    CARD = "card"
    CASH = "cash"
    TRANSFER = "transfer"


class PaymentStatus(str, Enum):
    PAID = "paid"
    REFUNDED = "refunded"


ACTIVE_BOOKING_STATUSES = (BookingStatus.CONFIRMED,)
