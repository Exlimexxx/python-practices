"""Прикладной JSON-протокол (этап 5 методички).

Формат запроса::

    {"command": "get", "data": {"id": 3}}
    + "\n"

Формат ответа::

    {"status": "ok", "data": {...}}
    {"status": "error", "error": "текст", "code": "not_found"}

Границы сообщений определяются символом перевода строки
(newline-delimited JSON). Класс LineBuffer накапливает байты из recv()
и выдаёт только целые строки: TCP -- это поток байтов, а не сообщения.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Mapping

from exceptions import ProtocolError

#: Кодировка протокола.
ENCODING: str = "utf-8"

#: Разделитель сообщений.
DELIMITER: bytes = b"\n"

#: Полный список команд сервера (минимум 6 обязательных + дополнительные).
COMMANDS: tuple[str, ...] = (
    "list",
    "get",
    "create",
    "update",
    "delete",
    "average_grade",
    "groups",
    "status",
    "ping",
    "sleep",
)


def encode_message(payload: Mapping[str, Any]) -> bytes:
    """Сериализует словарь в JSON и добавляет разделитель сообщений."""
    try:
        text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        raise ProtocolError(f"Не удалось сериализовать сообщение: {exc}") from exc
    return text.encode(ENCODING) + DELIMITER


def decode_message(raw: str | bytes) -> Dict[str, Any]:
    """Разбирает одно сообщение протокола в словарь."""
    if isinstance(raw, bytes):
        try:
            raw = raw.decode(ENCODING)
        except UnicodeDecodeError as exc:
            raise ProtocolError("Сообщение не является корректным UTF-8") from exc

    text = raw.strip()
    if not text:
        raise ProtocolError("Получено пустое сообщение")

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ProtocolError(f"Некорректный JSON: {exc.msg} (позиция {exc.pos})") from exc

    if not isinstance(payload, dict):
        raise ProtocolError("Корневой элемент сообщения должен быть объектом JSON")
    return payload


@dataclass
class Request:
    """Разобранный запрос клиента."""

    command: str
    data: Dict[str, Any] = field(default_factory=dict)
    raw: str = ""

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "Request":
        """Проверяет обязательные поля command/data."""
        if not isinstance(payload, Mapping):
            raise ProtocolError("Запрос должен быть объектом JSON")

        if "command" not in payload:
            raise ProtocolError("В запросе отсутствует обязательное поле 'command'")

        command = payload["command"]
        if not isinstance(command, str) or not command.strip():
            raise ProtocolError("Поле 'command' должно быть непустой строкой")

        data = payload.get("data", {})
        if data is None:
            data = {}
        if not isinstance(data, Mapping):
            raise ProtocolError("Поле 'data' должно быть объектом JSON")

        if "command" in data:
            # распространённая ошибка новичков: поля перепутаны местами
            raise ProtocolError("Поле 'command' не должно находиться внутри 'data'")

        return cls(command=command.strip(), data=dict(data))

    @classmethod
    def parse(cls, raw: str | bytes) -> "Request":
        """Разбирает строку протокола целиком (JSON + проверка полей)."""
        payload = decode_message(raw)
        request = cls.from_dict(payload)
        request.raw = raw.decode(ENCODING) if isinstance(raw, bytes) else raw
        return request

    def to_dict(self) -> Dict[str, Any]:
        return {"command": self.command, "data": self.data}

    def encode(self) -> bytes:
        return encode_message(self.to_dict())


@dataclass
class Response:
    """Ответ сервера."""

    status: str
    data: Any = None
    error: str | None = None
    code: str | None = None

    @classmethod
    def ok(cls, data: Any = None) -> "Response":
        return cls(status="ok", data=data)

    @classmethod
    def error(cls, message: str, code: str = "app_error") -> "Response":
        return cls(status="error", error=message, code=code)

    @property
    def is_ok(self) -> bool:
        return self.status == "ok"

    def to_dict(self) -> Dict[str, Any]:
        if self.is_ok:
            return {"status": "ok", "data": self.data}
        payload: Dict[str, Any] = {"status": "error", "error": self.error}
        if self.code:
            payload["code"] = self.code
        return payload

    def encode(self) -> bytes:
        return encode_message(self.to_dict())

    @classmethod
    def parse(cls, raw: str | bytes) -> "Response":
        """Разбирает ответ сервера; проверяет обязательное поле status."""
        payload = decode_message(raw)
        status = payload.get("status")
        if status not in ("ok", "error"):
            raise ProtocolError("В ответе отсутствует корректное поле 'status'")
        if status == "ok":
            return cls(status="ok", data=payload.get("data"))
        return cls(
            status="error",
            error=str(payload.get("error", "неизвестная ошибка сервера")),
            code=payload.get("code"),
        )


class LineBuffer:
    """Накопитель байтов, выделяющий сообщения, разделённые '\n'.

    Именно этот класс решает проблему, описанную в п. 6 методички:
    TCP передаёт поток байтов, и только приложение знает, где заканчивается
    одно сообщение и начинается следующее.
    """

    def __init__(self) -> None:
        self._buffer: bytes = b""
        self.received_messages: int = 0

    def feed(self, chunk: bytes) -> List[str]:
        """Добавляет порцию байтов и возвращает список готовых сообщений."""
        if not chunk:
            return []
        self._buffer += chunk
        messages: List[str] = []
        while DELIMITER in self._buffer:
            raw_line, self._buffer = self._buffer.split(DELIMITER, 1)
            line = raw_line.strip()
            if not line:
                continue
            messages.append(line.decode(ENCODING))
        self.received_messages += len(messages)
        return messages

    def flush(self) -> List[str]:
        """Возвращает незавершённый остаток буфера (например, при закрытии)."""
        raw_line = self._buffer.strip()
        self._buffer = b""
        if not raw_line:
            return []
        return [raw_line.decode(ENCODING)]

    def reset(self) -> None:
        self._buffer = b""

    @property
    def pending_bytes(self) -> int:
        return len(self._buffer)


def iter_messages(raw_stream: bytes) -> Iterator[str]:
    """Вспомогательный генератор: разбирает поток байтов на сообщения."""
    buffer = LineBuffer()
    for message in buffer.feed(raw_stream):
        yield message
    for message in buffer.flush():
        yield message
