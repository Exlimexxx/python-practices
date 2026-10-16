"""TCP-клиент с консольным меню (этапы 7-9 методички).

Клиент умеет:
  * подключаться к серверу и корректно обрабатывать его недоступность;
  * формировать JSON-запрос вида {"command": ..., "data": {...}};
  * отправлять его и разбирать ответ {"status": "ok"/"error"};
  * работать в интерактивном меню;
  * работать в пакетном режиме (--batch): читает построчные JSON-запросы
    из stdin -- это нужно для автоматической демонстрации;
  * использовать тайм-аут (socket.settimeout) и переподключаться после него.

Примеры запуска::

    python client.py                          # интерактивное меню
    python client.py --batch < script.jsonl   # пакетный режим
"""

from __future__ import annotations

import argparse
import json
import logging
import socket
import sys
from typing import Any, Dict, Mapping, Optional

from exceptions import (
    RemoteTimeoutError,
    ServerUnavailableError,
)
from protocol import ENCODING, LineBuffer, Request, Response

LOGGER = logging.getLogger("practice9.client")

DEFAULT_TIMEOUT: float = 5.0


class StudentClient:
    """Сетевой клиент: отвечает только за обмен сообщениями с сервером."""

    def __init__(self, host: str = "127.0.0.1", port: int = 5509, timeout: float = DEFAULT_TIMEOUT) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self._socket: Optional[socket.socket] = None
        self._needs_reconnect: bool = False

    # ------------------------------------------------------------------
    # соединение
    # ------------------------------------------------------------------
    @property
    def connected(self) -> bool:
        return self._socket is not None

    def connect(self) -> None:
        """Устанавливает TCP-соединение; при неудаче -- ServerUnavailableError."""
        self.close()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        try:
            sock.connect((self.host, self.port))
        except (ConnectionRefusedError, socket.timeout, OSError) as exc:
            sock.close()
            raise ServerUnavailableError(
                f"Сервер {self.host}:{self.port} недоступен ({type(exc).__name__}: {exc})"
            ) from exc
        self._socket = sock
        self._needs_reconnect = False
        LOGGER.info("Подключение к серверу %s:%s установлено", self.host, self.port)

    def close(self) -> None:
        """Закрывает соединение, если оно открыто."""
        if self._socket is not None:
            try:
                self._socket.close()
            except OSError:  # pragma: no cover
                pass
            self._socket = None
            LOGGER.info("Соединение с сервером закрыто")

    def _ensure_connection(self) -> None:
        if self._socket is None or self._needs_reconnect:
            self.connect()

    # ------------------------------------------------------------------
    # обмен сообщениями
    # ------------------------------------------------------------------
    def send_raw(self, raw_text: str) -> Response:
        """Отправляет произвольную строку (нужно для демонстрации ошибок)."""
        self._ensure_connection()
        assert self._socket is not None
        LOGGER.info("Запрос к серверу: %s", raw_text)
        try:
            self._socket.sendall(raw_text.encode(ENCODING) + b"\n")
        except OSError as exc:
            self._needs_reconnect = True
            raise ServerUnavailableError(f"Соединение разорвано при отправке: {exc}") from exc
        return self._receive()

    def send(self, command: str, data: Optional[Mapping[str, Any]] = None) -> Response:
        """Отправляет команду протокола и возвращает разобранный ответ."""
        request = Request(command=command, data=dict(data or {}))
        raw_text = json.dumps(request.to_dict(), ensure_ascii=False)
        return self.send_raw(raw_text)

    def _receive(self) -> Response:
        """Читает ответ сервера до символа перевода строки."""
        assert self._socket is not None
        buffer = LineBuffer()
        try:
            while True:
                chunk = self._socket.recv(4096)
                if not chunk:
                    self._needs_reconnect = True
                    raise ServerUnavailableError("Сервер закрыл соединение")
                messages = buffer.feed(chunk)
                if messages:
                    response = Response.parse(messages[0])
                    LOGGER.info("Ответ сервера: %s", messages[0])
                    return response
        except socket.timeout as exc:
            # Демонстрация этапа 9: операция завершилась по тайм-ауту.
            self._needs_reconnect = True
            raise RemoteTimeoutError(
                f"Тайм-аут {self.timeout:.1f} с: сервер не ответил вовремя"
            ) from exc
        except ConnectionResetError as exc:
            self._needs_reconnect = True
            raise ServerUnavailableError(f"Соединение разорвано сервером: {exc}") from exc


class ClientApp:
    """Консольное приложение: меню, вывод запросов и ответов."""

    MENU = (
        "\n=== КЛИЕНТ: Университет (вариант 4) ===\n"
        " 1. list          -- список студентов (с необязательным фильтром)\n"
        " 2. get           -- получить студента по id\n"
        " 3. create        -- создать студента\n"
        " 4. update        -- изменить данные студента\n"
        " 5. delete        -- удалить студента\n"
        " 6. average_grade -- средний балл студента (спец. команда варианта)\n"
        " 7. groups        -- сводка по учебным группам\n"
        " 8. status        -- состояние сервера\n"
        " 9. timeout       -- демонстрация тайм-аута (sleep 3 с, тайм-аут 1 с)\n"
        " 0. выход\n"
    )

    def __init__(self, client: StudentClient, out: Any = None) -> None:
        self.client = client
        self.out = out or sys.stdout

    # ------------------------------------------------------------------
    # вывод
    # ------------------------------------------------------------------
    def _print(self, text: str = "") -> None:
        print(text, file=self.out, flush=True)

    def execute(self, command: str, data: Optional[Mapping[str, Any]] = None) -> Optional[Response]:
        """Отправляет команду и печатает запрос/ответ; ошибки не пробрасываются."""
        request = Request(command=command, data=dict(data or {}))
        self._print(">>> ЗАПРОС: " + json.dumps(request.to_dict(), ensure_ascii=False))
        try:
            response = self.client.send(command, data)
        except RemoteTimeoutError as exc:
            self._print(f"!!! ТАЙМ-АУТ: {exc}")
            return None
        except ServerUnavailableError as exc:
            self._print(f"!!! СЕРВЕР НЕДОСТУПЕН: {exc}")
            return None
        except Exception as exc:  # защита консольного приложения
            self._print(f"!!! ОШИБКА КЛИЕНТА: {type(exc).__name__}: {exc}")
            return None

        if response.is_ok:
            self._print("<<< ОТВЕТ (ok): " + json.dumps(response.data, ensure_ascii=False))
        else:
            self._print(f"<<< ОТВЕТ (error, код {response.code}): {response.error}")
        return response

    # ------------------------------------------------------------------
    # пакетный режим
    # ------------------------------------------------------------------
    def run_batch(self, stream: Any = None) -> int:
        """Читает строки: JSON-запрос, комментарий (#) или !raw <текст>."""
        stream = stream or sys.stdin
        processed = 0
        for line in stream:
            text = line.strip()
            if not text or text.startswith("#"):
                continue
            if text.startswith("!raw "):
                raw_text = text[5:].strip()
                self._print(">>> ЗАПРОС (сырая строка): " + raw_text)
                try:
                    response = self.client.send_raw(raw_text)
                except RemoteTimeoutError as exc:
                    self._print(f"!!! ТАЙМ-АУТ: {exc}")
                    processed += 1
                    continue
                except ServerUnavailableError as exc:
                    self._print(f"!!! СЕРВЕР НЕДОСТУПЕН: {exc}")
                    return 1
                self._print_response(response)
                processed += 1
                continue

            try:
                payload = json.loads(text)
            except json.JSONDecodeError as exc:
                self._print(f"!!! НЕКОРРЕКТНЫЙ JSON В СЦЕНАРИИ: {exc}")
                continue

            command = payload.get("command", "")
            data = payload.get("data", {})
            self.execute(command, data)
            processed += 1
        return 0 if processed else 1

    def _print_response(self, response: Response) -> None:
        if response.is_ok:
            self._print("<<< ОТВЕТ (ok): " + json.dumps(response.data, ensure_ascii=False))
        else:
            self._print(f"<<< ОТВЕТ (error, код {response.code}): {response.error}")

    # ------------------------------------------------------------------
    # интерактивное меню
    # ------------------------------------------------------------------
    def run_interactive(self) -> int:
        self._print(self.MENU)
        while True:
            try:
                choice = input("Введите команду: ").strip()
            except (EOFError, KeyboardInterrupt):
                self._print("\nЗавершение работы клиента")
                return 0

            if choice in ("0", "q", "exit", "выход"):
                self._print("Завершение работы клиента")
                return 0

            try:
                if choice == "1":
                    group = input("Группа (Enter -- все): ").strip()
                    self.execute("list", {"group": group} if group else {})
                elif choice == "2":
                    self.execute("get", {"id": self._ask("Введите id: ")})
                elif choice == "3":
                    self.execute("create", self._ask_student_fields())
                elif choice == "4":
                    identifier = self._ask("Введите id: ")
                    changes = self._ask_student_fields(partial=True)
                    changes["id"] = identifier
                    self.execute("update", changes)
                elif choice == "5":
                    self.execute("delete", {"id": self._ask("Введите id: ")})
                elif choice == "6":
                    self.execute("average_grade", {"id": self._ask("Введите id: ")})
                elif choice == "7":
                    group = input("Группа (Enter -- все): ").strip()
                    self.execute("groups", {"group": group} if group else {})
                elif choice == "8":
                    self.execute("status", {})
                elif choice == "9":
                    self._demo_timeout()
                else:
                    self._print("Неизвестный пункт меню. Введите число от 0 до 9.")
            except (EOFError, KeyboardInterrupt):
                self._print("\nЗавершение работы клиента")
                return 0

    def _ask(self, prompt: str, default: str = "") -> str:
        value = input(prompt).strip()
        return value or default

    def _ask_student_fields(self, partial: bool = False) -> Dict[str, Any]:
        """Спрашивает поля студента; при partial пустая строка = не менять."""
        suffix = " (Enter -- не изменять)" if partial else ""
        data: Dict[str, Any] = {}
        name = input(f"ФИО{suffix}: ").strip()
        group = input(f"Группа{suffix}: ").strip()
        grades = input(f"Оценки через пробел, например 5 4 3{suffix}: ").strip()
        email = input(f"E-mail{suffix}: ").strip()
        year = input(f"Курс 1-6{suffix}: ").strip()
        status = input(f"Статус active/academic_leave/expelled{suffix}: ").strip()

        if name:
            data["name"] = name
        if group:
            data["group"] = group
        if grades:
            data["grades"] = grades
        if email:
            data["email"] = email
        if year:
            data["year"] = year
        if status:
            data["status"] = status
        return data

    def _demo_timeout(self) -> None:
        """Создаёт отдельного клиента с малым тайм-аутом и усыпляет сервер."""
        short_client = StudentClient(self.client.host, self.client.port, timeout=1.0)
        short_app = ClientApp(short_client, out=self.out)
        self._print(
            "[ДЕМОНСТРАЦИЯ ТАЙМ-АУТА] создаём клиента с socket.settimeout(1.0) "
            "и просим сервер задержать ответ на 3 с"
        )
        try:
            short_client.connect()
            short_app.execute("sleep", {"seconds": 3})
        except ServerUnavailableError as exc:
            self._print(f"!!! СЕРВЕР НЕДОСТУПЕН: {exc}")
        finally:
            short_client.close()
        self._print("[ДЕМОНСТРАЦИЯ ТАЙМ-АУТА] соединение закрыто, основной клиент продолжает работу")


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TCP-клиент 'Университет' (ЛР9, вариант 4)")
    parser.add_argument("--host", default="127.0.0.1", help="адрес сервера")
    parser.add_argument("--port", type=int, default=5509, help="порт сервера")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="тайм-аут, с")
    parser.add_argument(
        "--batch",
        action="store_true",
        help="пакетный режим: читать JSON-запросы построчно из stdin",
    )
    parser.add_argument("--log-level", default="INFO", help="уровень логирования")
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, str(args.log_level).upper(), logging.INFO),
        format="%(asctime)s %(levelname)-7s [%(threadName)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stderr,
        force=True,
    )

    client = StudentClient(args.host, args.port, args.timeout)
    app = ClientApp(client)

    print(f"=== КЛИЕНТ УНИВЕРСИТЕТА === сервер {args.host}:{args.port}, тайм-аут {args.timeout} с")
    try:
        client.connect()
    except ServerUnavailableError as exc:
        print(f"[КЛИЕНТ] Ошибка подключения: {exc}")
        return 1

    try:
        if args.batch:
            return app.run_batch()
        return app.run_interactive()
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
