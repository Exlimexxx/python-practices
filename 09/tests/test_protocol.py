"""Тесты прикладного протокола (этап 12: минимум 1 тест протокола)."""

from __future__ import annotations

import json

import pytest

from exceptions import ProtocolError
from protocol import (
    LineBuffer,
    Request,
    Response,
    decode_message,
    encode_message,
)


def test_encode_decode_roundtrip_with_newline() -> None:
    """Сообщение кодируется в JSON + '\n' и разбирается обратно."""
    payload = {"command": "get", "data": {"id": 3}}

    encoded = encode_message(payload)

    assert encoded.endswith(b"\n")
    assert decode_message(encoded) == payload


def test_request_parse_and_encode() -> None:
    """Request проверяет обязательные поля и умеет кодироваться."""
    request = Request.parse('{"command": "list", "data": {}}')
    assert request.command == "list"
    assert request.data == {}
    assert request.encode() == b'{"command":"list","data":{}}\n'


def test_decode_invalid_json_raises_protocol_error() -> None:
    """Некорректный JSON -- ProtocolError."""
    with pytest.raises(ProtocolError):
        decode_message("{command: list}")


def test_request_without_command_raises_protocol_error() -> None:
    """Отсутствие поля command -- ProtocolError."""
    with pytest.raises(ProtocolError):
        Request.parse('{"data": {"id": 1}}')


def test_request_with_data_not_object_raises_protocol_error() -> None:
    """Поле data должно быть объектом."""
    with pytest.raises(ProtocolError):
        Request.parse('{"command": "list", "data": [1, 2, 3]}')


def test_response_ok_and_error_serialization() -> None:
    """Единый формат ответа: status/data или status/error."""
    ok = Response.ok({"count": 1})
    failure = Response.error("Студент не найден", "not_found")

    assert json.loads(ok.encode().decode()).keys() == {"status", "data"}
    assert json.loads(failure.encode().decode()) == {
        "status": "error",
        "error": "Студент не найден",
        "code": "not_found",
    }
    assert Response.parse(ok.encode()).is_ok
    assert Response.parse(failure.encode()).code == "not_found"


def test_line_buffer_splits_stream_into_messages() -> None:
    """TCP -- поток байтов: буфер собирает сообщения по символу '\n'."""
    buffer = LineBuffer()

    assert buffer.feed(b'{"command": "lis') == []
    messages = buffer.feed(b't", "data": {}}\n{"command": "ping", "data": {}}\n')
    assert messages == ['{"command": "list", "data": {}}', '{"command": "ping", "data": {}}']

    assert buffer.feed(b'{"command": "status"') == []
    assert buffer.flush() == ['{"command": "status"']
