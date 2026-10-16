"""Автоматическая демонстрация лабораторной работы №9 (вариант 4).

Скрипт запускает server.py через subprocess.Popen, дожидается готовности
порта, запускает клиентов с подготовленным stdin и сохраняет НАСТОЯЩИЙ
консольный вывод в файлы каталога demo/:

    demo/server_client.txt  -- сервер + клиент: 6+ успешных команд, ошибки,
                               недоступный сервер, ситуация тайм-аута;
    demo/clients3.txt       -- три клиента одновременно;
    demo/udp.txt            -- операция status по UDP;
    demo/pytest.txt         -- вывод запуска автотестов.

Запуск::

    python run_demo.py                # все четыре демонстрации
    python run_demo.py --only tcp     # только первая
"""

from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

BASE_DIR = Path(__file__).resolve().parent
DEMO_DIR = BASE_DIR / "demo"
SCRIPTS_DIR = DEMO_DIR / "scripts"
LOGS_DIR = DEMO_DIR / "logs"
PYTHON = sys.executable

HOST = "127.0.0.1"
PREFERRED_TCP_PORT = 5509
PREFERRED_UDP_PORT = 5509

SEPARATOR = "=" * 78
THIN = "-" * 78


# ======================================================================
# вспомогательные функции
# ======================================================================
def child_env() -> Dict[str, str]:
    """Окружение дочерних процессов: UTF-8 и небуферизованный вывод."""
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUNBUFFERED"] = "1"
    return env


def port_is_free(port: int, kind: str = "tcp") -> bool:
    """Проверяет, свободен ли порт указанного типа."""
    socket_type = socket.SOCK_STREAM if kind == "tcp" else socket.SOCK_DGRAM
    with socket.socket(socket.AF_INET, socket_type) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((HOST, port))
        except OSError:
            return False
    return True


def find_free_port(kind: str = "tcp") -> int:
    """Возвращает свободный порт, выделенный операционной системой."""
    socket_type = socket.SOCK_STREAM if kind == "tcp" else socket.SOCK_DGRAM
    with socket.socket(socket.AF_INET, socket_type) as sock:
        sock.bind((HOST, 0))
        return int(sock.getsockname()[1])


def pick_port(preferred: int, kind: str = "tcp") -> Tuple[int, str]:
    """Возвращает свободный порт: предпочтительный или выданный ОС."""
    if port_is_free(preferred, kind):
        return preferred, f"использован порт {preferred}"
    fallback = find_free_port(kind)
    return fallback, f"порт {preferred} занят, выбран свободный порт {fallback}"


def wait_for_port(port: int, timeout: float = 15.0) -> bool:
    """Ждёт, пока TCP-порт начнёт принимать соединения."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)
            try:
                sock.connect((HOST, port))
                return True
            except OSError:
                time.sleep(0.2)
    return False


def run_python(
    script: str,
    args: Sequence[str] = (),
    stdin_text: Optional[str] = None,
    stdin_file: Optional[Path] = None,
    timeout: float = 90.0,
) -> subprocess.CompletedProcess:
    """Запускает python-скрипт и возвращает результат с текстовым выводом."""
    command = [PYTHON, "-u", str(BASE_DIR / script), *args]
    options = dict(
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        env=child_env(),
        cwd=str(BASE_DIR),
    )
    if stdin_file is not None:
        with open(stdin_file, "r", encoding="utf-8") as handle:
            return subprocess.run(command, stdin=handle, **options)
    if stdin_text is not None:
        return subprocess.run(command, input=stdin_text, **options)
    return subprocess.run(command, stdin=subprocess.DEVNULL, **options)


def launch_client(
    args: Sequence[str], stdin_file: Path
) -> Tuple[subprocess.Popen, object]:
    """Запускает клиента в фоне, читая stdin из файла (для 3 клиентов сразу)."""
    handle = open(stdin_file, "r", encoding="utf-8")
    process = subprocess.Popen(
        [PYTHON, "-u", str(BASE_DIR / "client.py"), *args],
        stdin=handle,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=child_env(),
        cwd=str(BASE_DIR),
    )
    return process, handle


def start_server(log_path: Path, tcp_port: int, udp_port: int, seed: bool = True) -> subprocess.Popen:
    """Запускает server.py в фоне, весь вывод -- в файл журнала."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_handle = open(log_path, "w", encoding="utf-8")
    command = [
        PYTHON,
        "-u",
        str(BASE_DIR / "server.py"),
        "--host",
        HOST,
        "--port",
        str(tcp_port),
        "--udp-port",
        str(udp_port),
    ]
    if seed:
        command.append("--seed")
    process = subprocess.Popen(
        command,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        env=child_env(),
        cwd=str(BASE_DIR),
    )
    setattr(process, "_log_handle", log_handle)
    return process


def server_command(tcp_port: int, udp_port: int, seed: bool = True) -> str:
    """Строка запуска сервера для отчёта."""
    tail = " --seed" if seed else ""
    return (
        f"python server.py --host {HOST} --port {tcp_port} --udp-port {udp_port}{tail}"
    )


def stop_server(process: subprocess.Popen) -> None:
    """Останавливает серверный процесс и закрывает файл журнала."""
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:  # pragma: no cover
            process.kill()
            process.wait(timeout=5)
    log_handle = getattr(process, "_log_handle", None)
    if log_handle is not None:
        log_handle.flush()
        log_handle.close()


def read_log(log_path: Path) -> str:
    """Читает журнал сервера после его остановки."""
    if not log_path.exists():
        return "<журнал не найден>"
    return log_path.read_text(encoding="utf-8", errors="replace").rstrip()


def format_result(result: subprocess.CompletedProcess) -> str:
    """Объединяет stdout и stderr запущенного процесса в один блок."""
    parts: List[str] = []
    if result.stdout.strip():
        parts.append(result.stdout.rstrip())
    if result.stderr.strip():
        parts.append("--- журнал клиента (stderr, модуль logging) ---")
        parts.append(result.stderr.rstrip())
    parts.append(f"--- код возврата: {result.returncode} ---")
    return "\n".join(parts)


def section(title: str) -> str:
    return f"\n{THIN}\n{title}\n{THIN}"


def write_demo(name: str, content: str) -> Path:
    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    path = DEMO_DIR / name
    path.write_text(content.rstrip() + "\n", encoding="utf-8")
    return path


def script_path(name: str, content: str) -> Path:
    SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    path = SCRIPTS_DIR / name
    path.write_text(content, encoding="utf-8")
    return path


def banner(title: str, extra: Sequence[str]) -> List[str]:
    lines = [
        SEPARATOR,
        title,
        f"Дата и время запуска: {time.strftime('%Y-%m-%d %H:%M:%S')}",
    ]
    lines.extend(extra)
    lines.append(SEPARATOR)
    return lines


# ======================================================================
# сценарии клиентов
# ======================================================================
DEMO1_BATCH = """# Сценарий пакетного клиента (каждая строка -- отдельный JSON-запрос).
# Строки, начинающиеся с '#', -- комментарии; '!raw ' отправляет строку как есть.
{"command": "ping", "data": {}}
{"command": "status", "data": {}}
{"command": "list", "data": {}}
{"command": "get", "data": {"id": 1}}
{"command": "average_grade", "data": {"id": 1}}
{"command": "average_grade", "data": {"id": 2}}
{"command": "average_grade", "data": {"id": 3}}
{"command": "create", "data": {"name": "Кузнецов Артём Игоревич", "group": "ИУ7-33Б", "grades": [5, 4, 5], "email": "kuznetsov@bmstu.ru", "year": 3}}
{"command": "get", "data": {"id": 4}}
{"command": "update", "data": {"id": 4, "grades": [5, 5, 5], "group": "ИУ7-34Б"}}
{"command": "average_grade", "data": {"id": 4}}
{"command": "groups", "data": {}}
{"command": "list", "data": {"group": "ИУ7-31Б", "sort_by": "average"}}
{"command": "delete", "data": {"id": 4}}
{"command": "get", "data": {"id": 4}}
{"command": "teleport", "data": {}}
!raw {"command": "create", "data": {"name": "Без группы"}}
!raw {"data": {"id": 1}}
!raw {это совсем не корректный JSON
{"command": "create", "data": {"name": "Плохие Оценки Студент", "group": "ИУ7-31Б", "grades": [9, 10]}}
{"command": "sleep", "data": {"seconds": 3}}
{"command": "ping", "data": {"echo": "клиент переподключился после тайм-аута"}}
{"command": "status", "data": {}}
"""

DEMO1_MENU = """1

2
1
6
1
8
7

0
"""

DEMO2_CLIENT1 = """# Клиент 1: работает со студентом id=1
{"command": "get", "data": {"id": 1}}
{"command": "average_grade", "data": {"id": 1}}
{"command": "sleep", "data": {"seconds": 1}}
{"command": "update", "data": {"id": 1, "email": "client1-new@bmstu.ru"}}
{"command": "list", "data": {"name_contains": "Иванов"}}
"""

DEMO2_CLIENT2 = """# Клиент 2: работает со студентом id=2 и создаёт нового
{"command": "get", "data": {"id": 2}}
{"command": "average_grade", "data": {"id": 2}}
{"command": "sleep", "data": {"seconds": 1}}
{"command": "create", "data": {"name": "Новый Студент Клиента Два", "group": "ИУ7-42Б", "grades": [4, 4, 5], "email": "new2@bmstu.ru", "year": 3}}
{"command": "groups", "data": {}}
"""

DEMO2_CLIENT3 = """# Клиент 3: работает со студентом id=3, создаёт нового и удаляет старого
{"command": "get", "data": {"id": 3}}
{"command": "average_grade", "data": {"id": 3}}
{"command": "sleep", "data": {"seconds": 1}}
{"command": "create", "data": {"name": "Новый Студент Клиента Три", "group": "ИУ7-43Б", "grades": [5, 5, 5], "email": "new3@bmstu.ru", "year": 3}}
{"command": "delete", "data": {"id": 3}}
{"command": "status", "data": {}}
"""

DEMO2_OBSERVER = """# Клиент-наблюдатель: выполняется после трёх параллельных клиентов
{"command": "list", "data": {}}
{"command": "status", "data": {}}
"""


def demo_server_client(tcp_port: int, udp_port: int) -> Path:
    """Демонстрация 1: сервер + клиент, ошибки, тайм-аут."""
    lines = banner(
        "ДЕМОНСТРАЦИЯ 1: TCP-сервер и TCP-клиент (ЛР9, вариант 4, «Университет»)",
        [
            f"Сервер: {HOST}:{tcp_port} (TCP), {HOST}:{udp_port} (UDP)",
            "Клиент запускается отдельным процессом: python client.py ...",
            "Весь вывод ниже -- реальный, полученный при выполнении скрипта.",
        ],
    )

    # --- 1. сервер недоступен -----------------------------------------
    dead_port = find_free_port()
    unavailable = run_python(
        "client.py",
        ["--port", str(dead_port), "--timeout", "2", "--batch"],
        stdin_text='{"command": "list", "data": {}}\n',
        timeout=30,
    )
    lines += [
        section(f"1. ОШИБКА «СЕРВЕР НЕДОСТУПЕН» (порт {dead_port}, никто не слушает)"),
        f"$ python client.py --port {dead_port} --timeout 2 --batch",
        'stdin: {"command": "list", "data": {}}',
        "",
        format_result(unavailable),
    ]

    # --- 2. запуск сервера --------------------------------------------
    log_path = LOGS_DIR / "server_demo1.log"
    process = start_server(log_path, tcp_port, udp_port, seed=True)
    ready = wait_for_port(tcp_port)
    lines += [
        section("2. ЗАПУСК СЕРВЕРА (фоновый процесс subprocess.Popen)"),
        f"$ {server_command(tcp_port, udp_port)}",
        f"Сервер готов принимать соединения: {'да' if ready else 'НЕТ'}",
    ]

    # --- 3. пакетный режим клиента ------------------------------------
    batch_script = script_path("demo1_batch.jsonl", DEMO1_BATCH)
    batch_result = run_python(
        "client.py",
        ["--port", str(tcp_port), "--timeout", "1.5", "--batch"],
        stdin_file=batch_script,
        timeout=120,
    )
    lines += [
        section("3. ОСНОВНОЙ СЦЕНАРИЙ КЛИЕНТА (пакетный режим, --batch, тайм-аут 1.5 с)"),
        "Сценарий: demo/scripts/demo1_batch.jsonl",
        "Команды: ping, status, list, get, average_grade x3, create, update, groups, delete,",
        "а также ошибки: объект не найден, неизвестная команда, некорректный JSON,",
        "отсутствующие поля, некорректные значения и ситуация тайм-аута.",
        "",
        format_result(batch_result),
    ]

    # --- 4. интерактивное меню ----------------------------------------
    menu_script = script_path("demo1_menu_stdin.txt", DEMO1_MENU)
    menu_result = run_python(
        "client.py",
        ["--port", str(tcp_port), "--timeout", "5"],
        stdin_file=menu_script,
        timeout=120,
    )
    lines += [
        section("4. КОНСОЛЬНОЕ МЕНЮ КЛИЕНТА (интерактивный режим, stdin из файла)"),
        "Входные строки: demo/scripts/demo1_menu_stdin.txt",
        "",
        format_result(menu_result),
    ]

    # --- 5. сервер жив после отключения клиентов ----------------------
    after_result = run_python(
        "client.py",
        ["--port", str(tcp_port), "--timeout", "5", "--batch"],
        stdin_text='{"command": "status", "data": {}}\n',
        timeout=30,
    )
    lines += [
        section("5. СЕРВЕР ПРОДОЛЖАЕТ РАБОТУ ПОСЛЕ ОТКЛЮЧЕНИЯ КЛИЕНТОВ"),
        "Все предыдущие клиенты уже завершились; новый клиент успешно получает статус.",
        "",
        format_result(after_result),
    ]

    # --- 6. журнал сервера --------------------------------------------
    stop_server(process)
    lines += [
        section("6. ПОЛНЫЙ ЖУРНАЛ СЕРВЕРА (модуль logging: запуск, подключения, команды, ошибки)"),
        read_log(log_path),
    ]

    # --- 7. освобождение порта ----------------------------------------
    lines += [
        section("7. ОСВОБОЖДЕНИЕ ПОРТА"),
        f"Порт {tcp_port} свободен после остановки сервера: "
        f"{'да' if port_is_free(tcp_port) else 'НЕТ'}",
    ]
    return write_demo("server_client.txt", "\n".join(lines))


def demo_three_clients(tcp_port: int, udp_port: int) -> Path:
    """Демонстрация 2: три клиента одновременно."""
    lines = banner(
        "ДЕМОНСТРАЦИЯ 2: ОДНОВРЕМЕННАЯ РАБОТА ТРЁХ КЛИЕНТОВ (этап 11)",
        [
            f"Сервер: {HOST}:{tcp_port} (TCP), потоковый пул ThreadPoolExecutor",
            "Три процесса client.py запускаются практически одновременно",
            "(subprocess.Popen + stdin из файла + перехват stdout/stderr).",
        ],
    )

    log_path = LOGS_DIR / "server_demo2.log"
    process = start_server(log_path, tcp_port, udp_port, seed=True)
    ready = wait_for_port(tcp_port)
    lines.append(f"Сервер готов принимать соединения: {'да' if ready else 'НЕТ'}")

    scripts = [
        ("Клиент 1", script_path("demo2_client1.jsonl", DEMO2_CLIENT1)),
        ("Клиент 2", script_path("demo2_client2.jsonl", DEMO2_CLIENT2)),
        ("Клиент 3", script_path("demo2_client3.jsonl", DEMO2_CLIENT3)),
    ]
    client_args = ["--port", str(tcp_port), "--timeout", "10", "--batch"]

    start_time = time.perf_counter()
    running: List[Tuple[str, subprocess.Popen, object, float]] = []
    for title, path in scripts:
        launched_at = time.perf_counter()
        proc, handle = launch_client(client_args, path)
        running.append((title, proc, handle, launched_at))

    outputs: List[Tuple[str, str, str, float, float, int]] = []
    for title, proc, handle, launched_at in running:
        stdout, stderr = proc.communicate(timeout=120)
        finished_at = time.perf_counter()
        handle.close()  # type: ignore[union-attr]
        outputs.append((title, stdout, stderr, launched_at, finished_at, proc.returncode))
    total_elapsed = time.perf_counter() - start_time

    lines.append(section("1. ХРОНОМЕТРАЖ (все три клиента работали параллельно)"))
    lines.append(f"{'Клиент':<10}{'старт, с':>10}{'финиш, с':>10}{'длительность, с':>18}{'код':>6}")
    durations = []
    for title, _stdout, _stderr, started, finished, code in outputs:
        duration = finished - started
        durations.append(duration)
        lines.append(
            f"{title:<10}{started - start_time:>10.2f}{finished - start_time:>10.2f}"
            f"{duration:>18.2f}{code:>6}"
        )
    lines.append(
        f"Суммарное время работы клиентов: {sum(durations):.2f} с; "
        f"фактическое время демонстрации: {total_elapsed:.2f} с."
    )
    lines.append(
        "Фактическое время существенно меньше суммы длительностей -- клиенты "
        "обслуживались сервером одновременно (команда sleep 1 с выполнялась параллельно)."
    )

    for title, stdout, stderr, _started, _finished, _code in outputs:
        lines.append(section(f"2. ВЫВОД {title.upper()}"))
        if stdout.strip():
            lines.append(stdout.rstrip())
        if stderr.strip():
            lines.append("--- журнал клиента (stderr, модуль logging) ---")
            lines.append(stderr.rstrip())

    observer = run_python(
        "client.py",
        ["--port", str(tcp_port), "--timeout", "5", "--batch"],
        stdin_text=DEMO2_OBSERVER,
        timeout=30,
    )
    lines += [
        section("3. КЛИЕНТ-НАБЛЮДАТЕЛЬ: общее хранилище после трёх параллельных клиентов"),
        format_result(observer),
    ]

    stop_server(process)
    lines += [
        section("4. ЖУРНАЛ СЕРВЕРА: три подключения и параллельные потоки client_0..client_2"),
        read_log(log_path),
        section("5. ОСВОБОЖДЕНИЕ ПОРТА"),
        f"Порт {tcp_port} свободен после остановки сервера: "
        f"{'да' if port_is_free(tcp_port) else 'НЕТ'}",
    ]
    return write_demo("clients3.txt", "\n".join(lines))


def demo_udp(udp_port: int, tcp_port: int) -> Path:
    """Демонстрация 3: операция status по UDP."""
    lines = banner(
        "ДЕМОНСТРАЦИЯ 3: UDP-ОПЕРАЦИЯ status (этап 20)",
        [
            f"Сервер слушает TCP {HOST}:{tcp_port} и UDP {HOST}:{udp_port}",
            "Запрос статуса не изменяет состояние системы (идемпотентная операция),",
            "поэтому для него допустимо отсутствие гарантированной доставки UDP.",
        ],
    )

    log_path = LOGS_DIR / "server_demo3.log"
    process = start_server(log_path, tcp_port, udp_port, seed=True)
    ready = wait_for_port(tcp_port)
    lines.append(f"TCP-сервер готов: {'да' if ready else 'НЕТ'}; UDP-сокет открыт тем же процессом")
    time.sleep(0.5)

    status_result = run_python("udp_client.py", ["--port", str(udp_port)], timeout=30)
    lines += [
        section("1. ШТАТНЫЙ ЗАПРОС СТАТУСА ПО UDP"),
        f"$ python udp_client.py --port {udp_port}",
        "",
        format_result(status_result),
    ]

    denied_result = run_python(
        "udp_client.py",
        ["--port", str(udp_port), "--message", '{"command": "delete", "data": {"id": 1}}'],
        timeout=30,
    )
    lines += [
        section("2. ОПЕРАЦИЯ, НЕДОСТУПНАЯ ПО UDP (только status)"),
        'датаграмма: {"command": "delete", "data": {"id": 1}}',
        "",
        format_result(denied_result),
    ]

    broken_result = run_python(
        "udp_client.py",
        ["--port", str(udp_port), "--message", "{это не корректный JSON"],
        timeout=30,
    )
    lines += [
        section("3. НЕКОРРЕКТНАЯ ДАТАГРАММА"),
        "датаграмма: {это не корректный JSON",
        "",
        format_result(broken_result),
    ]

    stop_server(process)
    lines += [
        section("4. ЖУРНАЛ СЕРВЕРА (TCP + UDP)"),
        read_log(log_path),
        section("5. ОСВОБОЖДЕНИЕ ПОРТОВ"),
        f"TCP-порт {tcp_port} свободен: {'да' if port_is_free(tcp_port) else 'НЕТ'}",
        f"UDP-порт {udp_port} свободен: {'да' if port_is_free(udp_port, 'udp') else 'НЕТ'}",
    ]
    return write_demo("udp.txt", "\n".join(lines))


def demo_pytest() -> Path:
    """Демонстрация 4: запуск автотестов."""
    command = [PYTHON, "-u", "-m", "pytest", "tests", "-v", "-p", "no:cacheprovider", "--color=no"]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
        env=child_env(),
        cwd=str(BASE_DIR),
    )
    lines = banner(
        "ДЕМОНСТРАЦИЯ 4: АВТОМАТИЧЕСКИЕ ТЕСТЫ (pytest)",
        [
            "Команда: python -m pytest tests -v -p no:cacheprovider --color=no",
            "Тесты: Repository (6), Service (9), Protocol (7), интеграционные (5).",
        ],
    )
    lines.append(result.stdout.rstrip())
    if result.stderr.strip():
        lines.append("--- stderr ---")
        lines.append(result.stderr.rstrip())
    lines.append(f"--- код возврата pytest: {result.returncode} ---")
    return write_demo("pytest.txt", "\n".join(lines))


# ======================================================================
# точка входа
# ======================================================================
def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Автодемонстрация ЛР9 (вариант 4)")
    parser.add_argument(
        "--only",
        choices=["tcp", "clients3", "udp", "pytest", "all"],
        default="all",
        help="какую демонстрацию выполнить",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    tcp_port, tcp_note = pick_port(PREFERRED_TCP_PORT, "tcp")
    udp_port, udp_note = pick_port(PREFERRED_UDP_PORT, "udp")
    print(f"[run_demo] TCP: {tcp_note}")
    print(f"[run_demo] UDP: {udp_note}")

    produced: List[Path] = []
    if args.only in ("tcp", "all"):
        produced.append(demo_server_client(tcp_port, udp_port))
    if args.only in ("clients3", "all"):
        produced.append(demo_three_clients(tcp_port, udp_port))
    if args.only in ("udp", "all"):
        produced.append(demo_udp(udp_port, tcp_port))
    if args.only in ("pytest", "all"):
        produced.append(demo_pytest())

    for path in produced:
        print(f"[run_demo] создан файл: {path.relative_to(BASE_DIR.parent.parent)}")

    print(
        "[run_demo] итоговая проверка портов: "
        f"TCP {tcp_port} свободен: {port_is_free(tcp_port)}, "
        f"UDP {udp_port} свободен: {port_is_free(udp_port, 'udp')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
