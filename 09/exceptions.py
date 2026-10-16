"""Собственные исключения приложения (этап 8 методички).

Иерархия:

    Exception
     +-- AppError                -- базовое прикладное исключение
          +-- ValidationError     -- некорректные значения параметров
          +-- NotFoundError       -- объект не найден
          +-- ConflictError       -- конфликт (например, дублирование id)
          +-- UnknownCommandError -- неизвестная команда протокола
          +-- ProtocolError       -- нарушение формата JSON-сообщения
          +-- RepositoryError     -- внутренняя ошибка хранилища

Дополнительно на стороне клиента используются:

    ServerUnavailableError -- сервер недоступен (ConnectionRefusedError);
    RemoteTimeoutError     -- истёк тайм-аут ожидания ответа (socket.timeout).

Все прикладные исключения несут машинный код (code) и текст (message),
которые напрямую превращаются в поле "error" ответа протокола.
"""

from __future__ import annotations

from typing import Any, Dict, Tuple


class AppError(Exception):
    """Базовое исключение предметной области с машинным кодом ошибки."""

    code: str = "app_error"

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message)
        self.message: str = message
        if code is not None:
            self.code = code

    def to_dict(self) -> Dict[str, Any]:
        """Представление исключения для JSON-ответа."""
        return {"code": self.code, "message": self.message}

    def __str__(self) -> str:  # pragma: no cover - тривиально
        return self.message


class ValidationError(AppError):
    """Некорректные значения параметров запроса."""

    code = "validation_error"


class NotFoundError(AppError):
    """Запрошенный объект отсутствует в хранилище."""

    code = "not_found"


class ConflictError(AppError):
    """Конфликт версий/идентификаторов объекта."""

    code = "conflict"


class UnknownCommandError(AppError):
    """Команда не поддерживается сервером."""

    code = "unknown_command"


class ProtocolError(AppError):
    """Нарушение формата сообщения прикладного протокола.

    Собственное исключение, требуемое этапом 8 лабораторной работы.
    Возникает при некорректном JSON, отсутствии обязательных полей,
    неверном типе полей, а также при ошибке декодирования байтов.
    """

    code = "protocol_error"


class RepositoryError(AppError):
    """Внутренняя ошибка слоя хранения."""

    code = "repository_error"


class ServerUnavailableError(AppError):
    """Сервер недоступен: соединение не установлено или разорвано."""

    code = "server_unavailable"


class RemoteTimeoutError(AppError):
    """Истёк тайм-аут ожидания ответа от сервера."""

    code = "timeout"


def describe_exception(exc: BaseException) -> Tuple[str, str]:
    """Возвращает пару (сообщение, код) для любого исключения.

    Для известных прикладных исключений используется их собственный код,
    для всех остальных -- internal_error.
    """
    if isinstance(exc, AppError):
        return exc.message, exc.code
    return f"{type(exc).__name__}: {exc}", "internal_error"
