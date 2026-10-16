"""TCP/UDP-сервер (этапы 6, 9, 10, 20 методички).

Обязанности модуля:
  * открыть TCP-сокет (AF_INET, SOCK_STREAM), выполнить bind() и listen();
  * принимать подключения и обслуживать НЕСКОЛЬКО клиентов одновременно
    (concurrent.futures.ThreadPoolExecutor);
  * разбирать newline-delimited JSON, вызывать Service и отправлять ответ;
  * использовать тайм-ауты (socket.settimeout);
  * вести подробный журнал через модуль logging;
  * продолжать работу после отключения любого клиента;
  * дополнительно обслуживать одну операцию по UDP (команда status).

Запуск::

    python server.py --host 127.0.0.1 --port 5509 --udp-port 5509
"""

from __future__ import annotations

import argparse
import logging
import socket
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, Mapping, Optional

from exceptions import (
    AppError,
    NotFoundError,
    ProtocolError,
    UnknownCommandError,
    ValidationError,
    describe_exception,
)
from protocol import COMMANDS, LineBuffer, Request, Response
from service import StudentService

LOGGER = logging.getLogger("practice9.server")

#: Сколько секунд ждать данные от уже подключённого клиента.
DEFAULT_CLIENT_TIMEOUT: float = 30.0

#: Период проверки флага остановки в цикле accept().
ACCEPT_POLL_INTERVAL: float = 0.5


def setup_logging(level: int = logging.INFO) -> None:
    """Единая настройка логирования для серверных и клиентских скриптов."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-7s [%(threadName)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
        force=True,
    )


class StudentTCPServer:
    """Многопоточный TCP-сервер предметной области "Университет"."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 5509,
        service: Optional[StudentService] = None,
        max_workers: int = 10,
        client_timeout: float = DEFAULT_CLIENT_TIMEOUT,
    ) -> None:
        self.host = host
        self.port = port
        self.service = service or StudentService()
        self.client_timeout = client_timeout
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="client"
        )
        self._server_socket: Optional[socket.socket] = None
        self._running = threading.Event()
        self._stats_lock = threading.Lock()
        self._total_connections = 0
        self._active_connections = 0
        self._handlers: Dict[str, Callable[[Mapping[str, Any]], Any]] = {
            "list": self._cmd_list,
            "get": self._cmd_get,
            "create": self._cmd_create,
            "update": self._cmd_update,
            "delete": self._cmd_delete,
            "average_grade": self._cmd_average_grade,
            "groups": self._cmd_groups,
            "status": self._cmd_status,
            "ping": self._cmd_ping,
        }

    # ==================================================================
    # жизненный цикл
    # ==================================================================
    def start(self) -> None:
        """Создаёт сокет, выполняет bind() и listen()."""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.host, self.port))
        server_socket.listen(16)
        server_socket.settimeout(ACCEPT_POLL_INTERVAL)
        self._server_socket = server_socket
        self._running.set()
        LOGGER.info(
            "Сервер запущен: %s:%s (тайм-аут клиента %.1f с, поддержано команд: %d)",
            self.host,
            self.port,
            self.client_timeout,
            len(COMMANDS),
        )

    def serve_forever(self) -> None:
        """Цикл accept(): каждая сессия уходит в отдельный поток."""
        if self._server_socket is None:
            raise RuntimeError("Сначала вызовите start()")

        while self._running.is_set():
            try:
                connection, address = self._server_socket.accept()
            except socket.timeout:
                continue
            except OSError:
                if self._running.is_set():
                    LOGGER.exception("Ошибка accept()")
                break

            with self._stats_lock:
                self._total_connections += 1
                self._active_connections += 1
            LOGGER.info(
                "Клиент подключён: %s:%s (всего подключений: %d, активных: %d)",
                address[0],
                address[1],
                self._total_connections,
                self._active_connections,
            )
            self._executor.submit(self._handle_client, connection, address)

    def shutdown(self, wait: bool = True) -> None:
        """Останавливает сервер и закрывает сокет."""
        self._running.clear()
        if self._server_socket is not None:
            try:
                self._server_socket.close()
            except OSError:  # pragma: no cover - закрытие уже закрытого сокета
                pass
            self._server_socket = None
        self._executor.shutdown(wait=wait)
        LOGGER.info("Сервер остановлен")

    # ==================================================================
    # обслуживание одного клиента
    # ==================================================================
    def _handle_client(self, connection: socket.socket, address: tuple[str, int]) -> None:
        """Читает поток newline-delimited JSON и отвечает на каждый запрос."""
        peer = f"{address[0]}:{address[1]}"
        buffer = LineBuffer()
        try:
            connection.settimeout(self.client_timeout)
            while self._running.is_set():
                try:
                    chunk = connection.recv(4096)
                except socket.timeout:
                    LOGGER.warning("Тайм-аут ожидания данных от клиента %s", peer)
                    break
                except ConnectionResetError:
                    LOGGER.warning("Соединение с клиентом %s разорвано", peer)
                    break

                if not chunk:
                    LOGGER.info("Клиент %s отключился (закрыл соединение)", peer)
                    break

                for raw_message in buffer.feed(chunk):
                    response = self._process_message(raw_message, peer)
                    try:
                        connection.sendall(response.encode())
                    except OSError:
                        LOGGER.warning("Не удалось отправить ответ клиенту %s", peer)
                        return
        except Exception:  # pragma: no cover - защита от неожиданных ошибок
            LOGGER.exception("Непредвиденная ошибка при обслуживании %s", peer)
        finally:
            with self._stats_lock:
                self._active_connections -= 1
            try:
                connection.close()
            except OSError:
                pass
            LOGGER.info("Соединение с %s закрыто", peer)

    def _process_message(self, raw_message: str, peer: str) -> Response:
        """Разбирает одно сообщение и выполняет команду (этапы 8 и 10)."""
        LOGGER.info("Получена команда от %s: %s", peer, raw_message)

        try:
            request = Request.parse(raw_message)
        except ProtocolError as exc:
            LOGGER.error("Ошибочный запрос от %s: %s", peer, exc.message)
            return Response.error(exc.message, exc.code)

        response = self.dispatch(request.command, request.data, peer=peer)
        if response.is_ok:
            LOGGER.info("Команда '%s' успешно выполнена для %s", request.command, peer)
        else:
            LOGGER.error(
                "Команда '%s' завершилась ошибкой для %s: %s",
                request.command,
                peer,
                response.error,
            )
        return response

    # ==================================================================
    # диспетчеризация команд
    # ==================================================================
    def dispatch(
        self, command: str, data: Mapping[str, Any], peer: str = "-"
    ) -> Response:
        """Вызывает обработчик команды, превращая исключения в ответ ошибки."""
        try:
            if command == "sleep":
                # Служебная команда: нужна только для демонстрации тайм-аута.
                return self._cmd_sleep(data, peer)

            handler = self._handlers.get(command)
            if handler is None:
                raise UnknownCommandError(
                    f"Неизвестная команда {command!r}. Доступны: {', '.join(COMMANDS)}"
                )

            if not isinstance(data, Mapping):
                raise ProtocolError("Поле 'data' должно быть объектом JSON")

            payload = handler(data)
            return Response.ok(payload)
        except AppError as exc:
            return Response.error(exc.message, exc.code)
        except Exception as exc:  # pragma: no cover - внутренние ошибки
            LOGGER.exception("Внутренняя ошибка при обработке команды %r", command)
            message, code = describe_exception(exc)
            return Response.error(message, code)

    # ------------------------------------------------------------------
    # обработчики команд
    # ------------------------------------------------------------------
    def _cmd_list(self, data: Mapping[str, Any]) -> Dict[str, Any]:
        students = self.service.list_students(data)
        return {
            "count": len(students),
            "students": [student.to_dict() for student in students],
        }

    def _cmd_get(self, data: Mapping[str, Any]) -> Dict[str, Any]:
        self._require_field(data, "id")
        student = self.service.get_student(data["id"])
        return {"student": student.to_dict()}

    def _cmd_create(self, data: Mapping[str, Any]) -> Dict[str, Any]:
        student = self.service.create_student(data)
        return {"student": student.to_dict(), "message": "Студент создан"}

    def _cmd_update(self, data: Mapping[str, Any]) -> Dict[str, Any]:
        self._require_field(data, "id")
        changes = {key: value for key, value in data.items() if key != "id"}
        if not changes:
            raise ValidationError("Не передано ни одного поля для изменения")
        student = self.service.update_student(data["id"], changes)
        return {"student": student.to_dict(), "message": "Данные студента обновлены"}

    def _cmd_delete(self, data: Mapping[str, Any]) -> Dict[str, Any]:
        self._require_field(data, "id")
        student = self.service.delete_student(data["id"])
        return {"student": student.to_dict(), "message": "Студент удалён"}

    def _cmd_average_grade(self, data: Mapping[str, Any]) -> Dict[str, Any]:
        self._require_field(data, "id")
        return self.service.average_grade(data["id"])

    def _cmd_groups(self, data: Mapping[str, Any]) -> Dict[str, Any]:
        return self.service.group_summary(data)

    def _cmd_status(self, data: Mapping[str, Any]) -> Dict[str, Any]:
        status = self.service.status()
        with self._stats_lock:
            status["active_connections"] = self._active_connections
            status["total_connections"] = self._total_connections
        return status

    def _cmd_ping(self, data: Mapping[str, Any]) -> Dict[str, Any]:
        answer = str(data.get("echo", "")) if isinstance(data, Mapping) else ""
        return {"pong": True, "echo": answer, "time": time.time()}

    def _cmd_sleep(self, data: Mapping[str, Any], peer: str) -> Response:
        """Демонстрация тайм-аута: сервер отвечает позже, чем ждёт клиент."""
        raw_seconds = data.get("seconds", 3)
        try:
            seconds = float(raw_seconds)
        except (TypeError, ValueError):
            return Response.error("Поле 'seconds' должно быть числом", "validation_error")
        if seconds < 0 or seconds > 30:
            return Response.error("Поле 'seconds' должно быть в диапазоне 0..30", "validation_error")

        LOGGER.warning("Команда sleep: сервер занят %.1f с (клиент %s)", seconds, peer)
        time.sleep(seconds)
        return Response.ok(
            {
                "slept_seconds": seconds,
                "note": "если клиент не дождался ответа -- сработал тайм-аут",
            }
        )

    @staticmethod
    def _require_field(data: Mapping[str, Any], field_name: str) -> None:
        if not isinstance(data, Mapping) or field_name not in data:
            raise ValidationError(
                f"Отсутствует обязательное поле '{field_name}' в data"
            )
        if data[field_name] is None:
            raise ValidationError(f"Поле '{field_name}' не может быть null")


class StudentUDPServer(threading.Thread):
    """UDP-сервер одной операции -- status (этап 20 методички).

    UDP выбран осознанно: запрос статуса является идемпотентным и
    "одноразовым". Потеря датаграммы не ломает состояние системы,
    клиент может просто повторить запрос, зато нет накладных расходов
    на установление соединения и подтверждения доставки.
    """

    def __init__(
        self,
        host: str,
        port: int,
        service: StudentService,
        poll_interval: float = 0.5,
    ) -> None:
        super().__init__(name="udp-server", daemon=True)
        self.host = host
        self.port = port
        self.service = service
        self.poll_interval = poll_interval
        self._stop_event = threading.Event()
        self._socket: Optional[socket.socket] = None
        self._handled = 0

    def run(self) -> None:
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        udp_socket.bind((self.host, self.port))
        udp_socket.settimeout(self.poll_interval)
        self._socket = udp_socket
        LOGGER.info("UDP-сервер запущен: %s:%s (команда: status)", self.host, self.port)

        while not self._stop_event.is_set():
            try:
                payload, address = udp_socket.recvfrom(4096)
            except socket.timeout:
                continue
            except OSError:  # сокет закрыт при остановке
                break

            LOGGER.info("UDP-датаграмма от %s:%s: %r", address[0], address[1], payload)
            response = self._handle_datagram(payload)
            try:
                udp_socket.sendto(response.encode(), address)
            except OSError:
                LOGGER.warning("Не удалось отправить UDP-ответ на %s:%s", *address)

        try:
            udp_socket.close()
        except OSError:  # pragma: no cover
            pass
        LOGGER.info("UDP-сервер остановлен (обработано датаграмм: %d)", self._handled)

    def _handle_datagram(self, payload: bytes) -> Response:
        """Обрабатывает одну датаграмму: поддерживается только status/ping."""
        self._handled += 1
        try:
            request = Request.parse(payload)
        except ProtocolError as exc:
            LOGGER.error("Ошибочная UDP-датаграмма: %s", exc.message)
            return Response.error(exc.message, exc.code)

        if request.command == "status":
            status = self.service.status()
            status["transport"] = "UDP"
            status["note"] = "доставка не гарантируется, но операция идемпотентна"
            return Response.ok(status)
        if request.command == "ping":
            return Response.ok({"pong": True, "transport": "UDP"})

        return Response.error(
            f"По UDP доступна только команда 'status', получено {request.command!r}",
            "unknown_command",
        )

    def stop(self) -> None:
        self._stop_event.set()
        self.join(timeout=3.0)


def build_service(seed: bool = False) -> StudentService:
    """Создаёт сервис, при необходимости наполняя его демо-данными."""
    service = StudentService()
    if seed:
        count = service.seed_demo_data()
        LOGGER.info("Загружены демонстрационные данные: %d студента", count)
    return service


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TCP/UDP-сервер 'Университет' (ЛР9, вариант 4)")
    parser.add_argument("--host", default="127.0.0.1", help="адрес прослушивания")
    parser.add_argument("--port", type=int, default=5509, help="TCP-порт")
    parser.add_argument("--udp-port", type=int, default=5509, help="UDP-порт")
    parser.add_argument("--no-udp", action="store_true", help="не запускать UDP-сервер")
    parser.add_argument("--seed", action="store_true", help="заполнить хранилище демо-данными")
    parser.add_argument(
        "--client-timeout",
        type=float,
        default=DEFAULT_CLIENT_TIMEOUT,
        help="тайм-аут ожидания данных клиента, с",
    )
    parser.add_argument("--log-level", default="INFO", help="уровень логирования")
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    setup_logging(getattr(logging, str(args.log_level).upper(), logging.INFO))

    service = build_service(seed=args.seed)
    tcp_server = StudentTCPServer(
        host=args.host,
        port=args.port,
        service=service,
        client_timeout=args.client_timeout,
    )
    udp_server: Optional[StudentUDPServer] = None

    tcp_server.start()
    if not args.no_udp:
        udp_server = StudentUDPServer(args.host, args.udp_port, service)
        udp_server.start()

    try:
        tcp_server.serve_forever()
    except KeyboardInterrupt:
        LOGGER.info("Получен Ctrl+C, завершение работы")
    finally:
        tcp_server.shutdown(wait=True)
        if udp_server is not None:
            udp_server.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
