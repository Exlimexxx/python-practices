"""Собственные исключения приложения.

Все ошибки наследуются от ``CinemaError``, что позволяет в ``main.py``
перехватывать их одним ``except`` и не завершать программу аварийно.
"""
from __future__ import annotations


class CinemaError(Exception):
    """Базовое исключение предметной области."""


class StorageUnavailableError(CinemaError):
    """Хранилище (MongoDB/Redis) недоступно и резервный режим отключён."""


class NotFoundError(CinemaError):
    """Документ не найден."""


class ValidationError(CinemaError):
    """Некорректные данные предметного объекта."""


class InvalidIdentifierError(CinemaError):
    """Некорректный идентификатор документа."""


class SerializationError(CinemaError):
    """Ошибка сериализации/десериализации документа."""
