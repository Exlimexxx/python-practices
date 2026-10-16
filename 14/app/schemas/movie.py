"""Pydantic-схемы для сущности «Фильм».

Разделены на:
* MovieCreate  — тело POST;
* MovieUpdate  — тело PATCH (все поля необязательные);
* MovieResponse — то, что видит клиент;
* MovieListResponse — постраничный список;
* MovieStats — статистика (п. 30 методички).
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class MovieBase(BaseModel):
    """Общие поля фильма с валидацией (п. 8 методички)."""

    title: str = Field(..., min_length=1, max_length=200, description="Название фильма")
    director: str = Field(..., min_length=1, max_length=200, description="Режиссёр")
    year: int = Field(..., ge=1888, le=2100, description="Год выпуска")
    genre: str = Field(..., min_length=1, max_length=100, description="Жанр")
    duration: int = Field(..., ge=1, le=600, description="Продолжительность в минутах")
    rating: float = Field(..., ge=0, le=10, description="Рейтинг от 0 до 10")
    description: str | None = Field(
        default=None, max_length=1000, description="Краткое описание фильма"
    )


class MovieCreate(MovieBase):
    """Модель тела запроса POST /movies."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Начало",
                "director": "Кристофер Нолан",
                "year": 2010,
                "genre": "фантастика",
                "duration": 148,
                "rating": 8.8,
                "description": "Вор проникает в сны, чтобы украсть идею.",
            }
        }
    )


class MovieUpdate(BaseModel):
    """Модель тела запроса PATCH /movies/{id} — изменяются только переданные поля."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    director: str | None = Field(default=None, min_length=1, max_length=200)
    year: int | None = Field(default=None, ge=1888, le=2100)
    genre: str | None = Field(default=None, min_length=1, max_length=100)
    duration: int | None = Field(default=None, ge=1, le=600)
    rating: float | None = Field(default=None, ge=0, le=10)
    description: str | None = Field(default=None, max_length=1000)


class MovieResponse(MovieBase):
    """Модель ответа с фильмом (включая id)."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Идентификатор фильма")


class MovieListResponse(BaseModel):
    """Постраничный список фильмов."""

    items: list[MovieResponse] = Field(..., description="Фильмы на текущей странице")
    total: int = Field(..., ge=0, description="Всего записей по фильтру")
    limit: int = Field(..., ge=1, description="Размер страницы")
    offset: int = Field(..., ge=0, description="Смещение")


class GenreStat(BaseModel):
    """Статистика по одному жанру."""

    genre: str
    count: int = Field(..., ge=0)


class MovieStats(BaseModel):
    """Статистика по коллекции фильмов."""

    total: int = Field(..., ge=0, description="Количество фильмов")
    average_rating: float | None = Field(None, description="Средний рейтинг")
    max_rating: float | None = Field(None, description="Максимальный рейтинг")
    min_rating: float | None = Field(None, description="Минимальный рейтинг")
    total_duration: int = Field(..., ge=0, description="Суммарная длительность, мин")
    by_genre: list[GenreStat] = Field(default_factory=list, description="Распределение по жанрам")


class ErrorResponse(BaseModel):
    """Единый формат ошибки (документируется в OpenAPI)."""

    error: dict = Field(..., description="Объект {code, message, details}")
