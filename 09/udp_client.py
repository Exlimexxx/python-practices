"""UDP-клиент одной операции -- status (этап 20 методички).

UDP не устанавливает соединение и не гарантирует доставку: это допустимо,
потому что запрос статуса идемпотентен (не изменяет состояние), а его
потеря приводит лишь к необходимости повторить запрос. Зато UDP не тратит
время на handshake и подтверждения, что важно для быстрых служебных проверок.

Запуск::

    python udp_client.py --port 5509
    python udp_client.py --message "{bad json"
"""

from __future__ import annotations

import argparse
import json
import socket
import sys
from typing import Optional

from protocol import ENCODING, Response

DEFAULT_TIMEOUT: float = 3.0


class UdpStatusClient:
    """Клиент UDP-операции status."""

    def __init__(self, host: str = "127.0.0.1", port: int = 5509, timeout: float = DEFAULT_TIMEOUT) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout

    def request_raw(self, payload: str) -> str:
        """Отправляет датаграмму и ждёт ответ; возвращает сырой текст ответа."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(self.timeout)
        try:
            sock.sendto(payload.encode(ENCODING) + b"\n", (self.host, self.port))
            data, _address = sock.recvfrom(4096)
        except socket.timeout as exc:
            raise TimeoutError(
                f"тайм-аут {self.timeout:.1f} с: UDP-ответ не получен"
            ) from exc
        finally:
            sock.close()
        return data.decode(ENCODING).strip()

    def status(self) -> Response:
        """Запрашивает статус сервера (команда status)."""
        payload = json.dumps({"command": "status", "data": {}}, ensure_ascii=False)
        return Response.parse(self.request_raw(payload))


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="UDP-клиент статуса сервера (ЛР9, вариант 4)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5509)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument(
        "--message",
        default=None,
        help="произвольная датаграмма вместо штатного запроса status",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    client = UdpStatusClient(args.host, args.port, args.timeout)
    payload = args.message if args.message is not None else json.dumps(
        {"command": "status", "data": {}}, ensure_ascii=False
    )

    print(f"=== UDP-КЛИЕНТ (команда status) === сервер {args.host}:{args.port}")
    print(f">>> ДАТАГРАММА: {payload}")
    try:
        raw_answer = client.request_raw(payload)
    except TimeoutError as exc:
        print(f"!!! ТАЙМ-АУТ UDP: {exc}")
        return 1

    print(f"<<< ДАТАГРАММА: {raw_answer}")
    try:
        response = Response.parse(raw_answer)
        if response.is_ok:
            print("<<< РАЗОБРАННЫЙ ОТВЕТ (ok): " + json.dumps(response.data, ensure_ascii=False))
        else:
            print(f"<<< РАЗОБРАННЫЙ ОТВЕТ (error, код {response.code}): {response.error}")
    except Exception as exc:
        print(f"!!! НЕ УДАЛОСЬ РАЗОБРАТЬ ОТВЕТ: {type(exc).__name__}: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
