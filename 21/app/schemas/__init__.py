"""Pydantic-схемы: валидация входных данных и формат ответов API."""
from __future__ import annotations

from app.schemas.booking import (
    BookingCancelRequest,
    BookingCreate,
    BookingOut,
    BookingPage,
    BookingSort,
    BookingStatusUpdate,
    BookingFilter,
)
from app.schemas.common import ErrorResponse, Page
from app.schemas.payment import PaymentCreate, PaymentOut
from app.schemas.report import ReportSummary
from app.schemas.room import (
    RoomCreate,
    RoomFilter,
    RoomOut,
    RoomPage,
    RoomSort,
    RoomUpdate,
)
from app.schemas.user import (
    AdminUserCreate,
    TokenResponse,
    UserLogin,
    UserOut,
    UserRegister,
)

__all__ = [
    "AdminUserCreate",
    "BookingCancelRequest",
    "BookingCreate",
    "BookingFilter",
    "BookingOut",
    "BookingPage",
    "BookingSort",
    "BookingStatusUpdate",
    "ErrorResponse",
    "Page",
    "PaymentCreate",
    "PaymentOut",
    "ReportSummary",
    "RoomCreate",
    "RoomFilter",
    "RoomOut",
    "RoomPage",
    "RoomSort",
    "RoomUpdate",
    "TokenResponse",
    "UserLogin",
    "UserOut",
    "UserRegister",
]
