"""Общие схемы ответов."""
from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

ItemT = TypeVar("ItemT")


class ErrorResponse(BaseModel):
    """Единый формат ошибки API."""

    error: str = Field(examples=["ROOM_NOT_FOUND"])
    message: str = Field(examples=["Номер с идентификатором 15 не найден"])
    details: dict | None = None


class Page(BaseModel, Generic[ItemT]):
    """Постраничная выборка."""

    total: int = Field(ge=0, description="Общее количество записей по фильтру")
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
    items: list[ItemT]
