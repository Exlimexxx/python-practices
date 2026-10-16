# -*- coding: utf-8 -*-
"""Формирует реальные файлы демонстраций для отчёта.

Скрипт запускает:
1) Flask-сервер (app.py, порт 5010) и client.py с подготовленным сценарием ввода
   -> demo/client.txt;
2) pytest -> demo/pytest.txt.

Скрипт не является частью REST API, он нужен только для получения
достоверных результатов выполнения (без ручного копирования консоли).
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from pathlib import Path

#: Регулярное выражение для удаления ANSI-последовательностей раскраски Werkzeug.
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

PROJECT_DIR: Path = Path(__file__).resolve().parent
DEMO_DIR: Path = PROJECT_DIR / "demo"
PYTHON: str = sys.executable
BASE_URL: str = "http://127.0.0.1:5010"

#: Сценарий ввода для client.py: список, создание, получение, PUT, PATCH,
#: фильтрация, сортировка, спец. операция, удаление, 404, 400, 405.
SCENARIO_LINES: list[str] = [
    "1",                                                              # GET /movies
    "3", "Интерстеллар", "фантастика", "169", "8.6", "550",           # POST /movies (id=7)
    "2", "7",                                                         # GET /movies/7
    "4", "7", "Интерстеллар (режиссёрская версия)", "фантастика", "169", "9.0", "600",  # PUT
    "5", "7", "", "", "", "9.3", "",                                   # PATCH (только rating)
    "7", "фантастика", "8.5", "",                                      # фильтрация
    "8", "price", "desc",                                              # сортировка
    "9", "фантастика",                                                 # GET /movies/by-genre
    "6", "7",                                                         # DELETE /movies/7
    "2", "999",                                                       # 404
    "3", "", "фантастика", "-5", "11", "550",                          # 400 (валидация)
    "10",                                                             # 405
    "0",                                                              # выход
]
SCENARIO: str = "\n".join(SCENARIO_LINES) + "\n"


def strip_ansi(text: str) -> str:
    """Убирает управляющие последовательности раскраски из вывода Werkzeug."""
    return ANSI_RE.sub("", text)


def build_env() -> dict[str, str]:
    """Переменные окружения с UTF-8, чтобы кириллица не ломалась."""
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["MOVIE_API_URL"] = BASE_URL
    env["NO_COLOR"] = "1"                 # отключает ANSI-раскраску журнала Werkzeug
    env["ANSI_COLORS_DISABLED"] = "1"
    return env


def wait_for_server(timeout: float = 20.0) -> bool:
    """Ждёт, пока Flask-сервер начнёт отвечать на GET /movies."""
    import requests

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if requests.get(BASE_URL + "/movies", timeout=1.0).status_code == 200:
                return True
        except requests.RequestException:
            time.sleep(0.2)
    return False


def run_client_demo() -> Path:
    """Запускает сервер и клиент, сохраняет объединённый вывод в demo/client.txt."""
    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    env = build_env()
    parts: list[str] = [
        "=" * 72,
        " ДЕМОНСТРАЦИЯ 1. Запуск Flask-сервера (порт 5010) и работа client.py",
        "=" * 72,
        f"Команда запуска сервера: {PYTHON} app.py",
        f"Адрес API: {BASE_URL}/movies",
        "",
    ]

    server = subprocess.Popen(
        [PYTHON, "-u", "app.py"],
        cwd=PROJECT_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    try:
        ready = wait_for_server()
        parts.append("Ожидание готовности сервера: " + ("успешно (GET /movies -> 200)" if ready else "ТАЙМ-АУТ"))
        parts.append("")
        parts.append("Сценарий ввода client.py:")
        for line in SCENARIO_LINES:
            parts.append("    " + (line if line else "<пустая строка>"))
        parts.append("")
        parts.append("-" * 72)
        parts.append(" Вывод client.py")
        parts.append("-" * 72)

        result = subprocess.run(
            [PYTHON, "-u", "client.py"],
            cwd=PROJECT_DIR,
            input=SCENARIO,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
        parts.append(result.stdout.rstrip("\n"))
        if result.stderr.strip():
            parts.append("[stderr] " + result.stderr.rstrip("\n"))
        parts.append("")
        parts.append(f"Код возврата client.py: {result.returncode}")
    finally:
        server.terminate()
        try:
            server_output, _ = server.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
            server_output, _ = server.communicate()

    parts.append("")
    parts.append("-" * 72)
    parts.append(" Лог Flask-сервера (stdout + stderr)")
    parts.append("-" * 72)
    parts.append(strip_ansi(server_output or "").rstrip("\n"))
    parts.append("")

    path = DEMO_DIR / "client.txt"
    path.write_text(strip_ansi("\n".join(parts)) + "\n", encoding="utf-8")
    return path


def run_pytest_demo() -> Path:
    """Запускает pytest и сохраняет вывод в demo/pytest.txt."""
    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    env = build_env()
    header = [
        "=" * 72,
        " ДЕМОНСТРАЦИЯ 2. Автоматические тесты pytest",
        "=" * 72,
        f"Команда: {PYTHON} -m pytest -v",
        "",
    ]
    result = subprocess.run(
        [PYTHON, "-m", "pytest", "-v"],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    text = "\n".join(header) + result.stdout + result.stderr + f"Код возврата pytest: {result.returncode}\n"

    path = DEMO_DIR / "pytest.txt"
    path.write_text(text, encoding="utf-8")
    return path


def main() -> int:
    """Точка входа: формирует оба файла демонстраций."""
    client_path = run_client_demo()
    pytest_path = run_pytest_demo()
    print("Файлы демонстраций обновлены:")
    print(" -", client_path)
    print(" -", pytest_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
