"""Схемы бронирований."""
from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field, model_validator

from app.models.enums import BookingStatus
from app.schemas.common import Page

MAX_BOOKING_NIGHTS = 365


class BookingSort(str, Enum):
    CREATED_DESC = "created_desc"
    CHECK_IN_ASC = "check_in_asc"
    CHECK_IN_DESC = "check_in_desc"
    PRICE_DESC = "price_desc"


class BookingCreate(BaseModel):
    room_id: int = Field(gt=0)
    check_in: date
    check_out: date
    comment: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def check_period(self) -> BookingCreate:
        if self.check_out <= self.check_in:
            raise ValueError("Дата выезда должна быть позже даты заезда")
        nights = (self.check_out - self.check_in).days
        if nights > MAX_BOOKING_NIGHTS:
            raise ValueError(
                f"Период бронирования не может превышать {MAX_BOOKING_NIGHTS} ночей"
            )
        return self


class BookingFilter(BaseModel):
    """Параметры поиска и сортировки бронирований."""

    status: BookingStatus | None = None
    user_id: int | None = Field(default=None, gt=0)
    room_id: int | None = Field(default=None, gt=0)
    check_in_from: date | None = None
    check_in_to: date | None = None
    sort: BookingSort = BookingSort.CREATED_DESC
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def check_date_range(self) -> BookingFilter:
        if (
            self.check_in_from is not None
            and self.check_in_to is not None
            and self.check_in_from > self.check_in_to
        ):
            raise ValueError("check_in_from не может быть позже check_in_to")
        return self


class BookingStatusUpdate(BaseModel):
    status: BookingStatus


class BookingCancelRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class BookingOut(BaseModel):
    id: int
    user_id: int
    user_email: str
    room_id: int
    room_number: str
    check_in: date
    check_out: date
    nights: int
    price_total: float
    paid_total: float
    remaining_amount: float
    status: BookingStatus
    comment: str | None = None
    created_at: datetime


class BookingPage(Page[BookingOut]):
    pass
