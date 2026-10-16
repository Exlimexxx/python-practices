"""Схемы гостиничных номеров, фильтрации и сортировки."""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import RoomStatus, RoomType
from app.schemas.common import Page


class RoomSort(str, Enum):
    NUMBER_ASC = "number_asc"
    PRICE_ASC = "price_asc"
    PRICE_DESC = "price_desc"
    CAPACITY_DESC = "capacity_desc"


class RoomCreate(BaseModel):
    number: str = Field(min_length=1, max_length=16, pattern=r"^[0-9A-Za-z\-]+$")
    room_type: RoomType = RoomType.STANDARD
    capacity: int = Field(ge=1, le=10)
    price_per_night: float = Field(gt=0, le=1_000_000)
    floor: int = Field(default=1, ge=1, le=100)
    status: RoomStatus = RoomStatus.AVAILABLE
    description: str | None = Field(default=None, max_length=500)


class RoomUpdate(BaseModel):
    """Частичное обновление номера."""

    room_type: RoomType | None = None
    capacity: int | None = Field(default=None, ge=1, le=10)
    price_per_night: float | None = Field(default=None, gt=0, le=1_000_000)
    floor: int | None = Field(default=None, ge=1, le=100)
    status: RoomStatus | None = None
    description: str | None = Field(default=None, max_length=500)


class RoomFilter(BaseModel):
    """Параметры поиска, фильтрации и сортировки номеров."""

    room_type: RoomType | None = None
    status: RoomStatus | None = None
    min_price: float | None = Field(default=None, ge=0)
    max_price: float | None = Field(default=None, ge=0)
    min_capacity: int | None = Field(default=None, ge=1, le=10)
    floor: int | None = Field(default=None, ge=1, le=100)
    sort: RoomSort = RoomSort.NUMBER_ASC
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def check_price_range(self) -> RoomFilter:
        if (
            self.min_price is not None
            and self.max_price is not None
            and self.min_price > self.max_price
        ):
            raise ValueError("min_price не может быть больше max_price")
        return self


class RoomOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    number: str
    room_type: RoomType
    capacity: int
    price_per_night: float
    floor: int
    status: RoomStatus
    description: str | None = None
    created_at: datetime


class RoomPage(Page[RoomOut]):
    pass
