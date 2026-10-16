"""Собственные исключения приложения и единый формат ошибок."""
from __future__ import annotations

from typing import Any


def error_payload(code: str, message: str, details: Any = None) -> dict:
    """Единый формат тела ошибки для всех ответов API.

    Пример::

        {"error": {"code": "movie_not_found",
                   "message": "Фильм с id=42 не найден",
                   "details": null}}
    """
    return {"error": {"code": code, "message": message, "details": details}}


class AppError(Exception):
    """Базовое доменное исключение приложения."""

    status_code: int = 500
    code: str = "internal_error"

    def __init__(self, message: str, details: Any = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details

    def to_payload(self) -> dict:
        return error_payload(self.code, self.message, self.details)


class MovieNotFoundError(AppError):
    """Фильм с указанным идентификатором отсутствует в БД."""

    status_code = 404
    code = "movie_not_found"

    def __init__(self, movie_id: int) -> None:
        super().__init__(f"Фильм с id={movie_id} не найден", {"movie_id": movie_id})


class DuplicateMovieError(AppError):
    """Попытка создать дубликат фильма."""

    status_code = 409
    code = "movie_duplicate"


class InvalidQueryError(AppError):
    """Некорректные параметры фильтрации/сортировки/пагинации (HTTP 400)."""

    status_code = 400
    code = "invalid_query"


class DatabaseError(AppError):
    """Ошибка уровня базы данных (HTTP 500)."""

    status_code = 500
    code = "database_error"


class CacheError(AppError):
    """Ошибка работы с кэшем (HTTP 500)."""

    status_code = 500
    code = "cache_error"
