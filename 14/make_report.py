"""Генерация итогового отчёта report.json (лабораторная №14, вариант 4).

Скрипт собирает структуру отчёта и сохраняет её через json.dump(...),
затем повторно читает файл через json.load для проверки корректности.
"""
from __future__ import annotations

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent


def codefile(caption: str, rel: str) -> dict:
    return {"type": "codefile", "caption": caption, "path": f"work/practice14/{rel}"}


def outputfile(caption: str, rel: str) -> dict:
    return {
        "type": "outputfile",
        "caption": f"Результат выполнения: {caption}",
        "path": f"work/practice14/{rel}",
    }


PROJECT_TREE = """work/practice14/
├── app/
│   ├── main.py               # сборка FastAPI, middleware, обработчики ошибок
│   ├── config.py             # настройки из переменных окружения
│   ├── database.py           # engine, Session, get_db, UDF casefold для SQLite
│   ├── cache.py              # CacheBackend, RedisCache, InMemoryCache
│   ├── exceptions.py         # свои исключения + единый формат ошибок
│   ├── logging_config.py     # настройка logging
│   ├── models/movie.py       # ORM-модель Movie (SQLAlchemy 2.0)
│   ├── schemas/movie.py      # Pydantic-схемы Create/Update/Response/List/Stats
│   ├── repositories/movie.py # доступ к БД (все SQL-запросы здесь)
│   ├── services/movie.py     # бизнес-логика + кэширование
│   └── routers/movies.py     # HTTP-слой (endpoints)
├── tests/
│   ├── conftest.py           # фикстуры (TestClient, тестовая БД, in-memory кэш)
│   └── test_api.py           # 28 автотестов
├── demo/
│   ├── run_api_demo.py       # поднимает uvicorn и делает реальные HTTP-запросы
│   ├── run_pytest_demo.py    # запускает pytest и сохраняет вывод
│   ├── api.txt               # реальный лог запросов/ответов
│   ├── openapi.txt           # выгрузка /openapi.json
│   └── pytest.txt            # реальный вывод pytest
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── requirements.txt
├── README.md
└── make_report.py
"""

ENDPOINTS = """GET    /movies                  — список: фильтры genre, min_rating, year; sort, order; limit, offset
GET    /movies/{id}               — один фильм (кэш Redis -> fallback in-memory)
POST   /movies                    — создание, HTTP 201
PUT    /movies/{id}               — полная замена
PATCH  /movies/{id}               — частичное изменение
DELETE /movies/{id}               — удаление, HTTP 204
GET    /movies/by-genre?genre=    — фильмы по жанру (специальная операция варианта)
GET    /movies/search?q=          — поиск по названию/режиссёру/описанию
GET    /movies/stats              — статистика (async def)
GET    /docs, /redoc, /openapi.json — документация
"""

ERRS = """400 invalid_query     — некорректное поле/направление сортировки, пустой поиск
404 movie_not_found   — фильм не найден
404 not_found         — несуществующий маршрут
409 movie_duplicate   — дубликат (заготовка под уникальные ключи)
422 validation_error  — ошибка валидации Pydantic
500 internal_error    — внутренняя ошибка (без traceback клиенту)
"""


def build() -> dict:
    blocks: list[dict] = []

    blocks.append({
        "type": "label",
        "label": "Ход работы (вариант 4)",
        "text": (
            "Разработка REST API «Кинотеатр — фильмы» на FastAPI: Pydantic-схемы, "
            "SQLAlchemy ORM (SQLite), слои router/service/repository/model, Dependency Injection, "
            "кэширование через Redis с fallback на in-memory, автотесты pytest, Docker-конфигурация."
        ),
    })

    blocks.append({"type": "heading", "text": "1. Постановка задачи (вариант 4)"})
    blocks.append({
        "type": "text",
        "text": (
            "Предметная область — кинотеатр, основная сущность — фильм, ресурс /movies. "
            "Поля фильма: название (title), режиссёр (director), год (year), жанр (genre), "
            "продолжительность (duration, мин), рейтинг (rating, 0..10), описание (description). "
            "API должно поддерживать создание, чтение списка и объекта по id, полное и частичное "
            "обновление, удаление, фильтрацию, поиск, сортировку, пагинацию и статистику. "
            "Специальные операции варианта: фильмы по жанру, поиск, сортировка, пагинация."
        ),
    })

    blocks.append({"type": "heading", "text": "2. Реализованные endpoints"})
    blocks.append({"type": "code", "caption": "Таблица маршрутов", "text": ENDPOINTS})
    blocks.append({
        "type": "text",
        "text": (
            "Коды состояния: 200 (чтение/обновление), 201 (создание), 204 (удаление), "
            "400 (некорректный запрос), 404 (не найдено), 422 (ошибка валидации), 500 (внутренняя ошибка). "
            "Все ошибки приведены к единому формату: "
            '{"error": {"code": ..., "message": ..., "details": ...}}.'
        ),
    })
    blocks.append({"type": "code", "caption": "Единые коды ошибок", "text": ERRS})

    blocks.append({"type": "heading", "text": "3. Архитектура и структура проекта"})
    blocks.append({
        "type": "text",
        "text": (
            "Код разделён на слои: HTTP -> Router -> Service -> Repository -> SQLAlchemy -> БД. "
            "Router не содержит SQL-запросов, Repository не знает про HTTP, Service хранит бизнес-логику "
            "и работает с кэшем. Связывание выполняется через Depends (Dependency Injection). "
            "Хранилище — SQLite через SQLAlchemy ORM (допускается методичкой для локального варианта)."
        ),
    })
    blocks.append({"type": "code", "caption": "Структура проекта", "text": PROJECT_TREE})

    blocks.append({"type": "heading", "text": "4. Конфигурация и подключение к базе данных"})
    blocks.append({"type": "text", "text": (
        "Все настройки (DATABASE_URL, REDIS_URL, APP_ENV, CACHE_TTL и др.) читаются из переменных "
        "окружения — в коде нет жёстко прописанных параметров подключения. Для SQLite дополнительно "
        "регистрируется UDF casefold(), чтобы поиск и фильтрация по кириллице не зависели от регистра: "
        "встроенный LIKE в SQLite учитывает регистр только для латиницы."
    )})
    blocks.append(codefile("app/config.py", "app/config.py"))
    blocks.append(codefile("app/database.py", "app/database.py"))

    blocks.append({"type": "heading", "text": "5. ORM-модель фильма"})
    blocks.append(codefile("app/models/movie.py", "app/models/movie.py"))

    blocks.append({"type": "heading", "text": "6. Pydantic-схемы и валидация"})
    blocks.append({"type": "text", "text": (
        "Схемы разделяют вход и выход API: MovieCreate (POST), MovieUpdate (PATCH, все поля "
        "необязательные), MovieResponse (ответ, from_attributes=True), MovieListResponse "
        "(items + total + limit + offset), MovieStats и GenreStat. Ограничения заданы через Field: "
        "year 1888..2100, duration 1..600, rating 0..10, длины строк."
    )})
    blocks.append(codefile("app/schemas/movie.py", "app/schemas/movie.py"))

    blocks.append({"type": "heading", "text": "7. Собственные исключения"})
    blocks.append({
        "type": "text",
        "text": (
            "Иерархия AppError -> MovieNotFoundError(404), DuplicateMovieError(409), "
            "InvalidQueryError(400), DatabaseError(500), CacheError(500). Каждое исключение несёт "
            "код и сообщение, а обработчики в main.py превращают их в единый JSON-формат."
        ),
    })
    blocks.append(codefile("app/exceptions.py", "app/exceptions.py"))

    blocks.append({"type": "heading", "text": "8. Слой доступа к данным (Repository)"})
    blocks.append(codefile("app/repositories/movie.py", "app/repositories/movie.py"))

    blocks.append({"type": "heading", "text": "9. Бизнес-логика и кэширование (Service)"})
    blocks.append({
        "type": "text",
        "text": (
            "Service валидирует параметры сортировки (иначе 400), собирает ответы, управляет кэшем. "
            "Метод get_movie объявлен как async def: сначала проверяется кэш (HIT -> сразу ответ), "
            "при промахе читается БД и результат кладётся в кэш. При PUT/PATCH/DELETE кэш "
            "инвалидируется. Метод get_stats выполняет синхронный доступ к SQLAlchemy в отдельном "
            "потоке через asyncio.to_thread, чтобы не блокировать event loop."
        ),
    })
    blocks.append(codefile("app/services/movie.py", "app/services/movie.py"))

    blocks.append({"type": "heading", "text": "10. Кэш: Redis с fallback на in-memory"})
    blocks.append({
        "type": "text",
        "text": (
            "Абстракция CacheBackend имеет две реализации: RedisCache (redis.asyncio) и InMemoryCache "
            "(словарь с TTL и счётчиками hit/miss). При старте приложение пытается подключиться к Redis; "
            "если сервер недоступен, пишется предупреждение и используется in-memory кэш — "
            "API продолжает работать. В демонстрации видно: «Redis недоступен ... Используется in-memory кэш», "
            "далее первый GET даёт cache MISS, повторный — cache HIT, а PATCH сбрасывает кэш."
        ),
    })
    blocks.append(codefile("app/cache.py", "app/cache.py"))

    blocks.append({"type": "heading", "text": "11. HTTP-слой (Router)"})
    blocks.append({
        "type": "text",
        "text": (
            "Роутер с префиксом /movies и тегом movies. Статические маршруты (/by-genre, /search, /stats) "
            "объявлены раньше динамического /{movie_id}. Для каждого endpoint указаны response_model, "
            "summary, description и документируемые коды ошибок. Сервис внедряется через "
            "Depends(get_movie_service), внутри которого используется Depends(get_db)."
        ),
    })
    blocks.append(codefile("app/routers/movies.py", "app/routers/movies.py"))

    blocks.append({"type": "heading", "text": "12. Сборка приложения, middleware и обработка ошибок"})
    blocks.append(codefile("app/main.py", "app/main.py"))
    blocks.append(codefile("app/logging_config.py", "app/logging_config.py"))

    blocks.append({"type": "heading", "text": "13. Асинхронность: пояснение"})
    blocks.append({
        "type": "text",
        "text": (
            "coroutine — объект, возвращаемый async def, который выполняется только при await. "
            "await приостанавливает выполнение корутины и отдаёт управление event loop, пока идёт "
            "операция ввода-вывода. event loop — планировщик, переключающий корутины. async def "
            "принципиально отличается от обычной функции тем, что не выполняется сразу при вызове. "
            "Асинхронность ускоряет I/O-bound задачи (БД, Redis, сеть, файлы), но CPU-bound вычисления "
            "от неё не ускоряются — они по-прежнему занимают поток; для них нужен пул процессов. "
            "В работе async def используются для GET /movies/{id}, /movies/stats и CRUD-операций."
        ),
    })

    blocks.append({"type": "heading", "text": "14. Автотесты (pytest, 28 тестов)"})
    blocks.append({
        "type": "text",
        "text": (
            "Тесты используют fastapi.testclient.TestClient, отдельную SQLite-БД и принудительный "
            "in-memory кэш (переменные окружения выставляются до импорта приложения). Проверены: список, "
            "получение, 404, создание (201), валидация (422), PUT, PATCH, DELETE и повторное удаление (404), "
            "фильтрация, сортировка asc/desc, некорректная сортировка (400), пагинация, поиск, статистика, "
            "cache hit/miss/invalidation и состав OpenAPI-схемы. Итог: 28 passed."
        ),
    })
    blocks.append(codefile("tests/conftest.py", "tests/conftest.py"))
    blocks.append(codefile("tests/test_api.py", "tests/test_api.py"))

    blocks.append({"type": "heading", "text": "15. Docker и зависимости"})
    blocks.append({
        "type": "text",
        "text": (
            "Docker в учебной среде отсутствует, поэтому конфигурация приложена без запуска. "
            "docker-compose.yml поднимает три сервиса: api (FastAPI), db (PostgreSQL 16) и cache (Redis 7); "
            "параметры подключения передаются приложению через переменные окружения."
        ),
    })
    blocks.append(codefile("Dockerfile", "Dockerfile"))
    blocks.append(codefile("docker-compose.yml", "docker-compose.yml"))
    blocks.append(codefile(".env.example", ".env.example"))
    blocks.append(codefile("requirements.txt", "requirements.txt"))
    blocks.append(codefile("README.md", "README.md"))

    blocks.append({"type": "heading", "text": "16. Демонстрационные скрипты"})
    blocks.append(codefile("demo/run_api_demo.py", "demo/run_api_demo.py"))
    blocks.append(codefile("demo/run_pytest_demo.py", "demo/run_pytest_demo.py"))

    blocks.append({"type": "heading", "text": "17. Результаты выполнения"})
    blocks.append({
        "type": "text",
        "text": (
            "Ниже приведён реальный вывод: запуск uvicorn на порту 8014, HTTP-запросы ко всем endpoints "
            "(включая 404, 400, 422), выгрузка OpenAPI-схемы и результат pytest. Вывод не редактировался."
        ),
    })
    blocks.append(outputfile("запуск uvicorn и HTTP-запросы ко всем endpoints", "demo/api.txt"))
    blocks.append(outputfile("выгрузка /openapi.json", "demo/openapi.txt"))
    blocks.append(outputfile("результат pytest (28 тестов)", "demo/pytest.txt"))

    blocks.append({"type": "heading", "text": "18. Соответствие требованиям"})
    blocks.append({"type": "text", "text": (
        "• FastAPI + Pydantic-схемы (Create/Update/Response/List/Stats), response_model и валидация — выполнено.\n"
        "• Все обязательные endpoints и специализированные операции варианта — выполнено.\n"
        "• HTTPException/обработчики и коды 200/201/204/400/404/409/422/500 с единым форматом ошибок — выполнено.\n"
        "• Разделение router/schemas/service/repository/model и Depends — выполнено.\n"
        "• SQLite через SQLAlchemy ORM, SQL отсутствует в router — выполнено.\n"
        "• Redis-кэш для GET /movies/{id} с fallback на in-memory и инвалидацией — выполнено.\n"
        "• async/await минимум в одном endpoint (фактически во всех операциях чтения/записи) — выполнено.\n"
        "• Swagger/OpenAPI через /docs, /redoc, /openapi.json — выполнено.\n"
        "• pytest + TestClient, минимум 10 тестов — 28 тестов, все проходят.\n"
        "• Dockerfile и docker-compose.yml приложены (Docker в среде отсутствует).\n"
        "• Логирование метод/URL/статус/время/ошибки — реализовано middleware и логгерами."
    )})

    blocks.append({"type": "heading", "text": "19. Вывод"})
    blocks.append({"type": "text", "text": (
        "В ходе работы спроектирован и реализован REST API кинотеатра на FastAPI. "
        "Приложение разделено на слои, использует SQLAlchemy ORM и Pydantic-валидацию, "
        "кэширует чтение через Redis с деградацией до in-memory, ведёт журнал и возвращает "
        "корректные HTTP-коды с единым форматом ошибок. Все 28 автотестов проходят, "
        "OpenAPI-документация корректно описывает все эндпоинты. Цель работы достигнута."
    )})

    return {
        "practice": 14,
        "title": "ПРАКТИЧЕСКАЯ РАБОТА №14",
        "subtitle": "Разработка REST API на Python с использованием FastAPI",
        "goal": (
            "Изучить разработку REST API на Python с помощью FastAPI: научиться описывать "
            "Pydantic-схемы и валидацию, строить слоистую архитектуру (router/service/repository/model), "
            "использовать SQLAlchemy ORM, Dependency Injection, кэширование Redis и автотесты pytest."
        ),
        "blocks": blocks,
    }


def main() -> None:
    allowed = {"label", "heading", "text", "code", "codefile", "outputfile"}
    report = build()
    for block in report["blocks"]:
        assert block["type"] in allowed, f"Недопустимый тип блока: {block['type']}"

    out = ROOT / "report.json"
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)

    # Проверка обратного чтения.
    with open(out, encoding="utf-8") as handle:
        loaded = json.load(handle)
    assert loaded["practice"] == 14
    assert len(loaded["blocks"]) == len(report["blocks"])
    print(f"report.json создан: {out}")
    print(f"Блоков: {len(loaded['blocks'])}")
    print(f"Размер: {out.stat().st_size} байт")


if __name__ == "__main__":
    main()
