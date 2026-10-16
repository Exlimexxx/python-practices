"""Демонстрационный скрипт: поднимает uvicorn и делает реальные HTTP-запросы.

Запуск (из каталога work/practice14)::

    python demo/run_api_demo.py

Результат сохраняется в demo/api.txt и demo/openapi.txt.
Скрипт поднимает сервер на порту 8014 в фоне и мягко его останавливает.
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import time

import httpx

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEMO_DIR = ROOT / "demo"
BASE_URL = "http://127.0.0.1:8014"
PORT = 8014
PYTHON = sys.executable

DEMO_DB = ROOT / "movies_demo.db"
SERVER_LOG = DEMO_DIR / "_uvicorn.log"

lines: list[str] = []


def log(text: str = "") -> None:
    """Печатает строку и запоминает её для итогового файла."""
    print(text)
    lines.append(text)


def hr(char: str = "=") -> None:
    log(char * 78)


def start_server() -> subprocess.Popen:
    """Запускает uvicorn в фоне, направляя его лог в файл."""
    if DEMO_DB.exists():
        DEMO_DB.unlink()

    env = os.environ.copy()
    env["DATABASE_URL"] = "sqlite:///./movies_demo.db"
    env["CACHE_BACKEND"] = "auto"
    env["REDIS_URL"] = "redis://localhost:6379/0"
    env["LOG_LEVEL"] = "INFO"
    # Чтобы лог uvicorn писался в UTF-8, а не в cp1251 консоли Windows.
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"

    log_file = open(SERVER_LOG, "w", encoding="utf-8")
    process = subprocess.Popen(
        [PYTHON, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(PORT)],
        cwd=str(ROOT),
        stdout=log_file,
        stderr=subprocess.STDOUT,
        env=env,
    )
    # Ждём готовности сервера
    for _ in range(60):
        if process.poll() is not None:
            raise RuntimeError("uvicorn завершился при запуске, см. demo/_uvicorn.log")
        try:
            response = httpx.get(f"{BASE_URL}/health", timeout=1.0, trust_env=False)
            if response.status_code == 200:
                return process
        except httpx.HTTPError:
            time.sleep(0.5)
    raise RuntimeError("Сервер не поднялся за 30 секунд")


def stop_server(process: subprocess.Popen) -> None:
    """Останавливает uvicorn (на Windows SIGINT не поддерживается — terminate)."""
    if process.poll() is None:
        process.terminate()
    try:
        process.wait(timeout=15)
    except subprocess.TimeoutExpired:  # pragma: no cover
        process.kill()
        process.wait(timeout=5)


def show(client: httpx.Client, method: str, path: str, title: str, json_body: dict | None = None) -> httpx.Response:
    """Выполняет запрос и печатает его описание + реальный ответ."""
    log()
    log(f"### {title}")
    log(f"--- {method} {BASE_URL}{path}")
    if json_body is not None:
        log("--- Request body:")
        log(json.dumps(json_body, ensure_ascii=False, indent=2))

    response = client.request(method, path, json=json_body)
    log(f"<-- HTTP {response.status_code} {response.reason_phrase}")
    if response.text:
        try:
            log(json.dumps(response.json(), ensure_ascii=False, indent=2))
        except json.JSONDecodeError:
            log(response.text[:800])
    else:
        log("(тело ответа отсутствует — 204 No Content)")
    return response


def main() -> None:
    # Консоль Windows может быть в cp1251 — принудительно переключаем на UTF-8.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):  # pragma: no cover
            pass

    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    log("Демонстрация работы REST API «Кинотеатр — фильмы» (лабораторная №14, вариант 4)")
    log(f"Python: {PYTHON}")
    log(f"Команда запуска: python -m uvicorn app.main:app --host 127.0.0.1 --port {PORT}")

    process = start_server()
    try:
        with httpx.Client(base_url=BASE_URL, timeout=15.0, trust_env=False) as client:
            hr()
            log("БЛОК 1. Сервисные endpoints")
            hr()
            show(client, "GET", "/", "Корневой endpoint")
            show(client, "GET", "/health", "Проверка состояния и активного кэша")
            show(client, "GET", "/docs", "Swagger UI (фрагмент HTML)")
            show(client, "GET", "/redoc", "ReDoc (фрагмент HTML)")

            hr()
            log("БЛОК 2. Создание фильмов (POST /movies, ожидается 201)")
            hr()
            movies = [
                {
                    "title": "Начало",
                    "director": "Кристофер Нолан",
                    "year": 2010,
                    "genre": "фантастика",
                    "duration": 148,
                    "rating": 8.8,
                    "description": "Вор проникает в сны, чтобы украсть идею.",
                },
                {
                    "title": "Матрица",
                    "director": "Лана Вачовски",
                    "year": 1999,
                    "genre": "фантастика",
                    "duration": 136,
                    "rating": 8.7,
                    "description": "Хакер узнаёт правду о реальности.",
                },
                {
                    "title": "Зелёная миля",
                    "director": "Фрэнк Дарабонт",
                    "year": 1999,
                    "genre": "драма",
                    "duration": 189,
                    "rating": 9.1,
                    "description": "История о заключённых и чудесном даре.",
                },
                {
                    "title": "Интерстеллар",
                    "director": "Кристофер Нолан",
                    "year": 2014,
                    "genre": "фантастика",
                    "duration": 169,
                    "rating": 8.6,
                    "description": "Путешествие сквозь червоточину ради спасения Земли.",
                },
            ]
            created_ids = []
            for movie in movies:
                response = show(client, "POST", "/movies", f"Создание фильма «{movie['title']}»", movie)
                if response.status_code == 201:
                    created_ids.append(response.json()["id"])

            hr()
            log("БЛОК 3. Список, фильтрация, сортировка, пагинация")
            hr()
            show(client, "GET", "/movies", "Полный список фильмов")
            show(client, "GET", "/movies?limit=2&offset=1", "Пагинация: limit=2, offset=1")
            show(client, "GET", "/movies?genre=фантастика", "Фильтр по жанру (кириллица, регистр не важен)")
            show(client, "GET", "/movies?min_rating=8.8", "Фильтр по минимальному рейтингу")
            show(client, "GET", "/movies?year=1999", "Фильтр по году выпуска")
            show(client, "GET", "/movies?sort=rating&order=desc&limit=3", "Сортировка по рейтингу по убыванию")
            show(client, "GET", "/movies?sort=year&order=asc", "Сортировка по году по возрастанию")

            hr()
            log("БЛОК 4. Специальные операции варианта")
            hr()
            show(client, "GET", "/movies/by-genre?genre=фантастика", "Фильмы по жанру (by-genre)")
            show(client, "GET", "/movies/search?q=нолан", "Поиск по режиссёру (регистронезависимо)")
            show(client, "GET", "/movies/search?q=Матрица", "Поиск по названию")
            show(client, "GET", "/movies/stats", "Статистика (async endpoint)")

            hr()
            log("БЛОК 5. Кэширование GET /movies/{id} (Redis с fallback на in-memory)")
            hr()
            first_id = created_ids[0]
            show(client, "GET", f"/movies/{first_id}", "Первый запрос — cache MISS (данные из БД)")
            show(client, "GET", f"/movies/{first_id}", "Повторный запрос — cache HIT")

            hr()
            log("БЛОК 6. PUT / PATCH / DELETE")
            hr()
            updated = {**movies[0], "title": "Начало (ремастер)", "rating": 9.0, "duration": 150}
            show(client, "PUT", f"/movies/{first_id}", "PUT: полная замена объекта", updated)
            show(client, "PATCH", f"/movies/{first_id}", "PATCH: изменяется только рейтинг", {"rating": 9.4})
            show(
                client,
                "DELETE",
                f"/movies/{created_ids[-1]}",
                "DELETE: успешное удаление (ожидается 204)",
            )
            show(
                client,
                "DELETE",
                f"/movies/{created_ids[-1]}",
                "DELETE: повторное удаление (ожидается 404)",
            )

            hr()
            log("БЛОК 7. Обработка ошибок (404 / 400 / 422)")
            hr()
            show(client, "GET", "/movies/999999", "404: фильм не найден")
            show(client, "GET", "/movies?sort=несуществующее_поле", "400: некорректное поле сортировки")
            show(client, "GET", "/movies?order=sideways", "400: некорректное направление сортировки")
            show(
                client,
                "POST",
                "/movies",
                "422: рейтинг вне диапазона 0..10",
                {**movies[0], "title": "Некорректный", "rating": 99},
            )
            show(
                client,
                "POST",
                "/movies",
                "422: отсутствует обязательное поле title",
                {"director": "Тест", "year": 2020, "genre": "тест", "duration": 90, "rating": 5.0},
            )
            show(client, "GET", "/unknown-endpoint", "404: несуществующий маршрут (единый формат ошибки)")

            hr()
            log("БЛОК 8. Выгрузка OpenAPI-схемы")
            hr()
            openapi = client.get("/openapi.json")
            schema = openapi.json()
            (DEMO_DIR / "openapi.txt").write_text(
                json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            log(f"GET {BASE_URL}/openapi.json -> HTTP {openapi.status_code}")
            log(f"Схема сохранена в demo/openapi.txt. Эндпоинтов: {len(schema['paths'])}")
            log("Пути:")
            for path, methods in schema["paths"].items():
                log(f"  {', '.join(m.upper() for m in methods)}  {path}")
            log("Схемы Pydantic: " + ", ".join(sorted(schema["components"]["schemas"])))
    finally:
        stop_server(process)

    # Добавляем в отчёт реальный лог сервера.
    hr()
    log("ЛОГ СЕРВЕРА UVICORN (реальный вывод процесса)")
    hr()
    if SERVER_LOG.exists():
        log(SERVER_LOG.read_text(encoding="utf-8", errors="replace"))
        SERVER_LOG.unlink()

    (DEMO_DIR / "api.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\nГотово: demo/api.txt, demo/openapi.txt")


if __name__ == "__main__":
    main()
