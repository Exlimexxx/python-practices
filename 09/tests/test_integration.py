"""Интеграционные тесты: Client -> TCP/UDP -> Server -> Service -> Repository.

Проверяют полную цепочку методички, одновременную работу нескольких
клиентов и ситуацию с тайм-аутом.
"""

from __future__ import annotations

import json
import socket
import threading
from typing import List

import pytest

from client import StudentClient
from exceptions import RemoteTimeoutError
from server import StudentTCPServer, StudentUDPServer
from service import StudentService


def free_tcp_port() -> int:
    """Возвращает свободный TCP-порт, выделенный операционной системой."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def free_udp_port() -> int:
    """Возвращает свободный UDP-порт."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class RunningServer:
    """Контекстный менеджер: поднимает TCP-сервер в отдельном потоке."""

    def __init__(self, seed: bool = False) -> None:
        self.port = free_tcp_port()
        self.service = StudentService()
        if seed:
            self.service.seed_demo_data()
        self.server = StudentTCPServer(port=self.port, service=self.service, client_timeout=5.0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self) -> "RunningServer":
        self.server.start()
        self.thread.start()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.server.shutdown(wait=True)
        self.thread.join(timeout=5.0)


def test_full_chain_create_get_average_delete() -> None:
    """Полный цикл: создание -> чтение -> average_grade -> изменение -> удаление."""
    with RunningServer() as running:
        client = StudentClient(port=running.port, timeout=3.0)
        client.connect()
        try:
            created = client.send(
                "create",
                {
                    "name": "Кузнецов Артём Игоревич",
                    "group": "ИУ7-33Б",
                    "grades": [5, 4, 5],
                    "email": "kuznetsov@bmstu.ru",
                    "year": 3,
                },
            )
            assert created.is_ok
            student_id = created.data["student"]["id"]

            fetched = client.send("get", {"id": student_id})
            assert fetched.is_ok
            assert fetched.data["student"]["name"] == "Кузнецов Артём Игоревич"

            average = client.send("average_grade", {"id": student_id})
            assert average.is_ok
            assert average.data["average_grade"] == 4.67

            updated = client.send("update", {"id": student_id, "grades": [5, 5, 5]})
            assert updated.is_ok
            assert updated.data["student"]["average_grade"] == 5.0

            deleted = client.send("delete", {"id": student_id})
            assert deleted.is_ok

            missing = client.send("get", {"id": student_id})
            assert not missing.is_ok
            assert missing.code == "not_found"
        finally:
            client.close()


def test_error_handling_unknown_command_and_bad_json() -> None:
    """Неизвестная команда, некорректный JSON и отсутствие полей."""
    with RunningServer() as running:
        client = StudentClient(port=running.port, timeout=3.0)
        client.connect()
        try:
            unknown = client.send("teleport", {})
            assert unknown.code == "unknown_command"

            broken = client.send_raw("{это не json")
            assert broken.code == "protocol_error"

            no_data = client.send("create", {"name": "Без группы"})
            assert no_data.code == "validation_error"

            not_found = client.send_raw('{"command": "get", "data": {"id": 4242}}')
            assert not_found.code == "not_found"
        finally:
            client.close()


def test_three_clients_work_concurrently() -> None:
    """Три клиента одновременно (этап 11) с общим хранилищем."""
    with RunningServer(seed=True) as running:
        results: List[bool] = []

        def worker(index: int) -> None:
            client = StudentClient(port=running.port, timeout=5.0)
            client.connect()
            try:
                created = client.send(
                    "create",
                    {
                        "name": f"Студентов Тест Номер{index}",
                        "group": f"ИУ7-3{index}Б",
                        "grades": [4, 4, 4],
                    },
                )
                assert created.is_ok
                listing = client.send("list", {})
                assert listing.is_ok
                assert listing.data["count"] >= 4
                results.append(True)
            finally:
                client.close()

        threads = [threading.Thread(target=worker, args=(index,)) for index in (1, 2, 3)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10.0)

        assert results == [True, True, True]
        assert running.service.status()["students_count"] == 6


def test_client_timeout_triggers_remote_timeout_error() -> None:
    """Сервер отвечает позже тайм-аута клиента -- RemoteTimeoutError."""
    with RunningServer() as running:
        client = StudentClient(port=running.port, timeout=0.5)
        client.connect()
        try:
            with pytest.raises(RemoteTimeoutError):
                client.send("sleep", {"seconds": 3})
        finally:
            client.close()


def test_udp_status_operation() -> None:
    """Дополнительная часть: команда status по UDP (этап 20)."""
    port = free_udp_port()
    service = StudentService()
    service.seed_demo_data()
    udp_server = StudentUDPServer("127.0.0.1", port, service)
    udp_server.start()

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(3.0)
            payload = json.dumps({"command": "status", "data": {}})
            sock.sendto((payload + "\n").encode("utf-8"), ("127.0.0.1", port))
            data, _ = sock.recvfrom(4096)

            answer = json.loads(data.decode("utf-8").strip())
            assert answer["status"] == "ok"
            assert answer["data"]["students_count"] == 3
            assert answer["data"]["transport"] == "UDP"

            sock.sendto(b'{"command": "delete", "data": {"id": 1}}\n', ("127.0.0.1", port))
            denied, _ = sock.recvfrom(4096)
            denied_answer = json.loads(denied.decode("utf-8").strip())
            assert denied_answer["status"] == "error"
            assert denied_answer["code"] == "unknown_command"
    finally:
        udp_server.stop()
