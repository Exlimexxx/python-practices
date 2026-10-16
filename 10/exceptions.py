# -*- coding: utf-8 -*-
"""Собственные исключения приложения (лабораторная работа №10, вариант 4).

Все исключения предметной области наследуются от класса ApiError, поэтому
HTTP-слой (Flask) умеет единообразно превращать их в JSON-ответ вида
{"error": "...", "code": "..."}.
"""
from __future__ import annotations

from typing import Any


class ApiError(Exception):
    """Базовое исключение приложения.

    :param message: текст ошибки (попадает в поле "error")
    :param code: машиночитаемый код ошибки (попадает в поле "code")
    :param status_code: HTTP-код ответа (по умолчанию берётся из класса)
    """

    status_code: int = 500
    default_code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, code: str | None = None, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or self.default_code
        if status_code is not None:
            self.status_code = status_code

    def to_dict(self) -> dict[str, Any]:
        """Представление ошибки в едином формате API."""
        return {"error": self.message, "code": self.code}

    def __str__(self) -> str:  # noqa: D105
        return f"[{self.code}] {self.message}"


class ValidationError(ApiError):
    """Некорректные данные запроса — 400 Bad Request."""

    status_code = 400
    default_code = "VALIDATION_ERROR"


class InvalidIdentifierError(ValidationError):
    """Некорректный идентификатор в пути — 400 Bad Request."""

    default_code = "INVALID_ID"


class NotFoundError(ApiError):
    """Объект не найден — 404 Not Found."""

    status_code = 404
    default_code = "MOVIE_NOT_FOUND"


class MethodNotAllowedError(ApiError):
    """HTTP-метод не поддерживается ресурсом — 405 Method Not Allowed."""

    status_code = 405
    default_code = "METHOD_NOT_ALLOWED"


class RepositoryError(ApiError):
    """Ошибка уровня хранения данных."""

    status_code = 500
    default_code = "REPOSITORY_ERROR"
