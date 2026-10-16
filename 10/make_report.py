# -*- coding: utf-8 -*-
"""Генерирует итоговый work/practice10/report.json для практической работы №10.

Запуск::

    python make_report.py

Скрипт собирает структуру отчёта (blocks) и записывает её через
json.dump(..., ensure_ascii=False, indent=2), после чего проверяет результат
через json.load и существование всех файлов, на которые ссылается отчёт.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SCRIPT_PATH = Path(__file__).resolve()
PROJECT_DIR = SCRIPT_PATH.parent
WORKSPACE = PROJECT_DIR.parents[1]
REPORT_PATH = PROJECT_DIR / "report.json"


def label(label_text: str, text: str) -> dict[str, Any]:
    """Абзац вида: <табуляция><жирная метка>: текст."""
    return {"type": "label", "label": label_text, "text": text}


def heading(text: str) -> dict[str, Any]:
    """Жирный подзаголовок."""
    return {"type": "heading", "text": text}


def paragraph(text: str) -> dict[str, Any]:
    """Обычный абзац."""
    return {"type": "text", "text": text}


def code(caption: str, text: str) -> dict[str, Any]:
    """Подпись + блок кода (моноширинный шрифт)."""
    return {"type": "code", "caption": caption, "text": text}


def codefile(caption: str, path: str) -> dict[str, Any]:
    """Подпись + код, читаемый из файла."""
    return {"type": "codefile", "caption": caption, "path": path}


def outputfile(caption: str, path: str) -> dict[str, Any]:
    """Подпись + реальный вывод программы из файла."""
    return {"type": "outputfile", "caption": caption, "path": path}


TREE = """work/practice10/
├── app.py                  # фабрика Flask-приложения, обработчики ошибок, middleware
├── routes.py               # HTTP-слой (Controller): endpoints ресурса /movies
├── models.py               # dataclass Movie (6 полей, id обязателен)
├── schemas.py              # сериализация, валидация, разбор query/path-параметров
├── repository.py           # MovieRepository — хранение в памяти, seed_movies()
├── service.py              # MovieService — бизнес-логика, фильтрация, сортировка
├── exceptions.py           # ApiError, ValidationError, NotFoundError, ...
├── client.py               # консольный HTTP-клиент на requests
├── run_demos.py            # генерация demo/client.txt и demo/pytest.txt
├── make_report.py          # генерация report.json
├── pytest.ini              # настройки pytest (pythonpath, testpaths)
├── requirements.txt        # зависимости (Flask, requests, pytest)
├── demo/
│   ├── client.txt          # реальный вывод: запуск сервера + client.py
│   └── pytest.txt          # реальный вывод pytest
└── tests/
    ├── conftest.py         # фикстуры application, client, service
    ├── test_repository.py  # 3 теста Repository
    ├── test_service.py     # 7 тестов Service
    └── test_api.py         # 12 тестов API (app.test_client())"""

API_TABLE = """Метод  | Endpoint                     | Назначение                               | Успешный код | Ошибки
-------+------------------------------+------------------------------------------+--------------+--------------
GET    | /movies                      | список фильмов (фильтрация и сортировка)  | 200          | 400
GET    | /movies/{id}                 | фильм по идентификатору (path-параметр)   | 200          | 400, 404
POST   | /movies                      | создание нового фильма                    | 201          | 400
PUT    | /movies/{id}                 | полное изменение фильма                   | 200          | 400, 404
PATCH  | /movies/{id}                 | частичное изменение фильма                | 200          | 400, 404
DELETE | /movies/{id}                 | удаление фильма                           | 204          | 400, 404
GET    | /movies/by-genre?genre=...   | фильмы по жанру (спец. операция)          | 200          | 400

Query-параметры списка: genre, min_rating, max_price, sort (price|rating|title|duration), order (asc|desc).
Метод, не поддерживаемый ресурсом (например, DELETE /movies), возвращает 405 Method Not Allowed."""

EXAMPLE_GET = """Запрос:
GET /movies?genre=фантастика&sort=rating&order=desc HTTP/1.1
Host: 127.0.0.1:5010
Accept: application/json

Ответ:
HTTP/1.1 200 OK
Content-Type: application/json

[
  {
    "id": 2,
    "title": "Начало",
    "genre": "фантастика",
    "duration": 148,
    "rating": 8.8,
    "price": 500.0
  },
  {
    "id": 1,
    "title": "Интерстеллар",
    "genre": "фантастика",
    "duration": 169,
    "rating": 8.6,
    "price": 550.0
  }
]"""

EXAMPLE_POST = """Запрос:
POST /movies HTTP/1.1
Host: 127.0.0.1:5010
Content-Type: application/json

{"title": "Дюна", "genre": "фантастика", "duration": 155, "rating": 8.3, "price": 600}

Ответ:
HTTP/1.1 201 Created
Location: /movies/7
Content-Type: application/json

{
  "id": 7,
  "title": "Дюна",
  "genre": "фантастика",
  "duration": 155,
  "rating": 8.3,
  "price": 600.0
}"""

EXAMPLE_PUT_PATCH = """PUT — полное изменение (все поля обязательны):
PUT /movies/7 HTTP/1.1
Content-Type: application/json
{"title": "Интерстеллар (режиссёрская версия)", "genre": "фантастика", "duration": 180, "rating": 9.0, "price": 600}

HTTP/1.1 200 OK
{"id": 7, "title": "Интерстеллар (режиссёрская версия)", "genre": "фантастика", "duration": 180, "rating": 9.0, "price": 600.0}

PATCH — частичное изменение (передаются только изменяемые поля):
PATCH /movies/7 HTTP/1.1
Content-Type: application/json
{"rating": 9.3}

HTTP/1.1 200 OK
{"id": 7, "title": "Интерстеллар (режиссёрская версия)", "genre": "фантастика", "duration": 180, "rating": 9.3, "price": 600.0}

DELETE — удаление:
DELETE /movies/7 HTTP/1.1

HTTP/1.1 204 No Content
(тело ответа отсутствует)"""

EXAMPLE_ERRORS = """404 Not Found — объекта нет:
GET /movies/999 HTTP/1.1
HTTP/1.1 404 NOT FOUND
{"error": "Фильм с id=999 не найден", "code": "MOVIE_NOT_FOUND"}

400 Bad Request — некорректные данные (объект не создаётся):
POST /movies HTTP/1.1
{"title": "", "genre": "фантастика", "duration": -5, "rating": 11, "price": 550}
HTTP/1.1 400 BAD REQUEST
{
  "error": "Некорректные данные: поле 'title' должно быть непустой строкой; поле 'duration' должно быть больше 0; поле 'rating' должно находиться в диапазоне от 0 до 10",
  "code": "VALIDATION_ERROR"
}

400 Bad Request — некорректный path-параметр:
GET /movies/abc HTTP/1.1
HTTP/1.1 400 BAD REQUEST
{"error": "Идентификатор 'abc' не является целым числом", "code": "INVALID_ID"}

405 Method Not Allowed — метод не поддерживается ресурсом:
DELETE /movies HTTP/1.1
HTTP/1.1 405 METHOD NOT ALLOWED
{"error": "HTTP-метод не поддерживается для данного ресурса", "code": "METHOD_NOT_ALLOWED"}"""

EXAMPLE_FILTER_SORT = """Фильтрация (три параметра, минимум два по заданию):
GET /movies?genre=фантастика
GET /movies?genre=фантастика&min_rating=8.5
GET /movies?max_price=450
GET /movies?genre=драма&min_rating=8.0&max_price=500

Сортировка (четыре поля, минимум два по заданию):
GET /movies?sort=price&order=desc
GET /movies?sort=rating&order=desc
GET /movies?sort=title&order=asc
GET /movies?sort=duration&order=asc

Пример ответа GET /movies?sort=price&order=desc (фрагмент):
HTTP/1.1 200 OK
[
  {"id": 7, "title": "Интерстеллар (режиссёрская версия)", "price": 600.0, "rating": 9.3},
  {"id": 1, "title": "Интерстеллар", "price": 550.0, "rating": 8.6},
  {"id": 6, "title": "Паразиты", "price": 520.0, "rating": 8.6},
  {"id": 2, "title": "Начало", "price": 500.0, "rating": 8.8}
]

Некорректные параметры дают 400:
GET /movies?sort=unknown            -> {"error": "Параметр 'sort' должен принимать значения: price, rating, title, duration", "code": "VALIDATION_ERROR"}
GET /movies?min_rating=abc          -> {"error": "Параметр 'min_rating' должен быть числом", "code": "VALIDATION_ERROR"}"""

EXAMPLE_SPECIAL = """Запрос:
GET /movies/by-genre?genre=фантастика HTTP/1.1
Host: 127.0.0.1:5010
Accept: application/json

Ответ:
HTTP/1.1 200 OK
Content-Type: application/json

{
  "genre": "фантастика",
  "count": 3,
  "movies": [
    {"id": 7, "title": "Интерстеллар (режиссёрская версия)", "genre": "фантастика", "duration": 169, "rating": 9.3, "price": 600.0},
    {"id": 2, "title": "Начало", "genre": "фантастика", "duration": 148, "rating": 8.8, "price": 500.0},
    {"id": 1, "title": "Интерстеллар", "genre": "фантастика", "duration": 169, "rating": 8.6, "price": 550.0}
  ]
}

Ответ отсортирован по убыванию рейтинга. Если жанр не найден, возвращается count = 0 и пустой список.
Запрос без параметра genre приводит к 400 Bad Request:
GET /movies/by-genre -> {"error": "Параметр 'genre' обязателен и не может быть пустым", "code": "VALIDATION_ERROR"}"""


def build_blocks() -> list[dict[str, Any]]:
    """Собирает все блоки отчёта в порядке следования."""
    blocks: list[dict[str, Any]] = []

    blocks.append(label(
        "Ход работы (вариант 4)",
        "В соответствии с индивидуальным заданием (вариант 4, таблица 30 методички) разработано клиент-серверное "
        "веб-приложение для предметной области «Кинотеатр». Основной ресурс — Movie (фильм) с шестью "
        "типизированными полями; специализированная операция — фильмы по жанру. Серверная часть реализована на "
        "Flask и предоставляет REST API, клиентская — консольная программа на requests.",
    ))
    blocks.append(label(
        "Предметная область",
        "Кинотеатр: каталог фильмов с указанием жанра, длительности, рейтинга и цены билета. Ресурс Movie: "
        "id (int), title (str), genre (str), duration (int, минуты), rating (float, 0..10), price (float, руб.).",
    ))
    blocks.append(label(
        "Специализированная операция",
        "GET /movies/by-genre?genre=... — возвращает фильмы выбранного жанра, количество найденных записей и "
        "список, отсортированный по убыванию рейтинга.",
    ))
    blocks.append(label(
        "Используемые технологии",
        "Python 3.13, Flask 3.1, requests 2.34, pytest 9.1, JSON, logging, dataclasses. База данных и ORM не "
        "используются: все данные хранятся в памяти процесса, внешние API не вызываются.",
    ))

    blocks.append(heading("Структура проекта"))
    blocks.append(code("Структура проекта", TREE))
    blocks.append(paragraph(
        "Проект разделён на слои: HTTP-слой (routes.py) принимает запрос и вызывает Service; Service (service.py) "
        "содержит бизнес-логику и валидацию; Repository (repository.py) хранит объекты в памяти. Модель описана "
        "в models.py, схемы и валидация — в schemas.py, собственные исключения — в exceptions.py. Точка входа — "
        "app.py, консольный клиент — client.py, автоматические тесты — в каталоге tests/.",
    ))

    blocks.append(heading("Описание API"))
    blocks.append(code("Таблица endpoints REST API", API_TABLE))

    blocks.append(heading("Листинг программы"))
    blocks.append(codefile("exceptions.py — собственные исключения", "work/practice10/exceptions.py"))
    blocks.append(codefile("models.py — модель предметной области", "work/practice10/models.py"))
    blocks.append(codefile("schemas.py — схемы и валидация", "work/practice10/schemas.py"))
    blocks.append(codefile("repository.py — хранилище в памяти", "work/practice10/repository.py"))
    blocks.append(codefile("service.py — бизнес-логика", "work/practice10/service.py"))
    blocks.append(codefile("routes.py — HTTP-слой (endpoints)", "work/practice10/routes.py"))
    blocks.append(codefile("app.py — фабрика Flask-приложения и обработка ошибок", "work/practice10/app.py"))
    blocks.append(codefile("client.py — консольный HTTP-клиент", "work/practice10/client.py"))
    blocks.append(codefile("tests/conftest.py — фикстуры pytest", "work/practice10/tests/conftest.py"))
    blocks.append(codefile("tests/test_repository.py — тесты Repository", "work/practice10/tests/test_repository.py"))
    blocks.append(codefile("tests/test_service.py — тесты Service", "work/practice10/tests/test_service.py"))
    blocks.append(codefile("tests/test_api.py — тесты REST API", "work/practice10/tests/test_api.py"))
    blocks.append(codefile("run_demos.py — получение реальных результатов запусков", "work/practice10/run_demos.py"))

    blocks.append(heading("Примеры HTTP-запросов и ответов"))
    blocks.append(code("Пример 1. GET /movies — получение списка с фильтрацией и сортировкой", EXAMPLE_GET))
    blocks.append(code("Пример 2. POST /movies — создание фильма", EXAMPLE_POST))
    blocks.append(code("Пример 3. PUT, PATCH и DELETE", EXAMPLE_PUT_PATCH))
    blocks.append(code("Пример 4. Фильтрация и сортировка", EXAMPLE_FILTER_SORT))
    blocks.append(code("Пример 5. Специализированная операция GET /movies/by-genre", EXAMPLE_SPECIAL))
    blocks.append(code("Пример 6. Ошибки 400, 404 и 405 (единый формат)", EXAMPLE_ERRORS))

    blocks.append(heading("Результаты выполнения"))
    blocks.append(paragraph(
        "Ниже приведены реальные результаты запусков (файлы сформированы скриптом run_demos.py, вывод не "
        "редактировался вручную). Сначала запускался Flask-сервер на порту 5010, затем клиент client.py со "
        "сценарием: список, создание, получение объекта, PUT, PATCH, фильтрация, сортировка, специализированная "
        "операция, удаление, ошибка 404, ошибка 400 и ошибка 405. После этого выполнялся pytest.",
    ))
    blocks.append(outputfile(
        "Результат выполнения: запуск сервера (порт 5010) и работа client.py",
        "work/practice10/demo/client.txt",
    ))
    blocks.append(outputfile(
        "Результат выполнения: pytest (22 теста)",
        "work/practice10/demo/pytest.txt",
    ))

    blocks.append(heading("Пояснения по требованиям методички"))
    blocks.append(label(
        "Архитектура и разделение слоёв",
        "Route/Controller (routes.py) только разбирает HTTP-запрос и вызывает методы Service, не содержит "
        "бизнес-логики и не обращается к Repository напрямую. Service (service.py) выполняет валидацию, "
        "фильтрацию, сортировку и специализированную операцию. Repository (repository.py) отвечает только за "
        "хранение объектов. Такое разделение видно в листингах.",
    ))
    blocks.append(label(
        "Хранение данных",
        "MovieRepository хранит фильмы в словаре {id: Movie} в оперативной памяти. База данных и ORM не "
        "используются, доступ потокобезопасен (threading.RLock). Для демонстрации предусмотрен начальный набор "
        "из шести фильмов (seed_movies).",
    ))
    blocks.append(label(
        "HTTP-методы и коды состояния",
        "Реализованы все обязательные операции: GET /movies (200), GET /movies/{id} (200), POST /movies (201), "
        "PUT /movies/{id} (200), PATCH /movies/{id} (200), DELETE /movies/{id} (204) и специализированный "
        "GET /movies/by-genre (200). Ошибки отдаются кодами 400 (некорректные данные или идентификатор), "
        "404 (объект или маршрут не найден) и 405 (метод не поддерживается ресурсом).",
    ))
    blocks.append(label(
        "Единый формат ошибки",
        "Все ошибки возвращаются объектом {\"error\": \"...\", \"code\": \"...\"}. Используемые коды: "
        "VALIDATION_ERROR, INVALID_ID, MOVIE_NOT_FOUND, METHOD_NOT_ALLOWED, NOT_FOUND, BAD_REQUEST, "
        "INTERNAL_ERROR. Обработчики зарегистрированы в app.py (register_error_handlers).",
    ))
    blocks.append(label(
        "Валидация входных данных",
        "title — непустая строка длиной до 200 символов; genre — непустая строка; duration — целое число "
        "больше 0 (не более 600); rating — число в диапазоне от 0 до 10; price — число больше 0. Проверяется "
        "также тип значений (bool не считается числом) и отсутствие неизвестных полей. При ошибке объект не "
        "создаётся и не изменяется, клиент получает 400 с перечислением нарушений.",
    ))
    blocks.append(label(
        "Фильтрация",
        "Поддерживается три фильтра: genre (жанр), min_rating (минимальный рейтинг) и max_price (максимальная "
        "цена). Фильтры комбинируются, что превышает требование «минимум два параметра».",
    ))
    blocks.append(label(
        "Сортировка",
        "Параметр sort принимает значения price, rating, title и duration (четыре поля вместо минимальных двух), "
        "параметр order — asc или desc. Сортировка по названию выполняется без учёта регистра. Некорректные "
        "значения параметров приводят к 400.",
    ))
    blocks.append(label(
        "Path- и query-параметры",
        "Идентификатор ресурса передаётся path-параметром (/movies/{id}), а фильтрация, сортировка и жанр для "
        "специализированной операции — query-параметрами. Некорректный path-параметр (например, /movies/abc) "
        "даёт 400 Bad Request с кодом INVALID_ID.",
    ))
    blocks.append(label(
        "HTTP-клиент",
        "client.py использует библиотеку requests и предоставляет консольное меню из пунктов: получить список, "
        "получить объект, создать, изменить (PUT), частично изменить (PATCH), удалить, фильтрация, сортировка, "
        "специализированная операция, проверка 405, выход. Для каждого запроса печатаются HTTP-метод, URL, тело "
        "запроса, код ответа и JSON-ответ, что видно в demo/client.txt.",
    ))
    blocks.append(label(
        "Тестирование",
        "Написано 22 автотеста pytest: 3 теста Repository, 7 тестов Service и 12 тестов API через "
        "app.test_client() (реальный сервер при этом не запускается). Проверены коды 200, 201, 204, 400, 404, "
        "405, операции PATCH и DELETE, фильтрация, сортировка, специализированный endpoint и единый формат "
        "ошибок. Все тесты проходят (см. demo/pytest.txt).",
    ))
    blocks.append(label(
        "Дополнительные возможности",
        "Реализованы: middleware-журналирование каждого запроса в формате «МЕТОД URL -> КОД -> время, мс» "
        "(дополнительное задание 4), заголовок ответа X-API-Version, заголовок Location при создании объекта, "
        "вывод JSON без экранирования кириллицы (ensure_ascii=False), а также метод бизнес-логики "
        "get_statistics со средней оценкой и ценой.",
    ))
    blocks.append(label(
        "Соответствие запретам методички",
        "База данных и ORM не используются; подключения к внешним API нет; готовые CRUD-шаблоны не "
        "применялись; вся система не размещена в одном файле (девять модулей приложения и каталог tests); "
        "HTTP-обработчики не обходят Service и Repository.",
    ))

    blocks.append(heading("Вывод"))
    blocks.append(paragraph(
        "В ходе работы изучены устройство HTTP-запроса и HTTP-ответа, методы GET, POST, PUT, PATCH и DELETE, "
        "коды состояния 200, 201, 204, 400, 404 и 405, заголовки, path- и query-параметры, принципы REST и "
        "stateless-взаимодействия. Разработано клиент-серверное веб-приложение для предметной области "
        "«Кинотеатр» (вариант 4): REST API на Flask с ресурсом Movie (шесть типизированных полей), слоями "
        "Route -> Service -> Repository и хранением данных в памяти, полным набором CRUD-операций, "
        "фильтрацией по трём параметрам, сортировкой по четырём полям, специализированной операцией "
        "GET /movies/by-genre и консольным HTTP-клиентом на requests. Написано 22 автоматических теста "
        "pytest, все они проходят. Реальные результаты запусков сервера, клиента и тестов сохранены в "
        "demo/client.txt и demo/pytest.txt. Цель работы достигнута полностью.",
    ))
    return blocks


def validate(report: dict[str, Any]) -> None:
    """Проверяет структуру отчёта и существование файлов, на которые он ссылается."""
    assert report["practice"] == 10
    assert isinstance(report["blocks"], list) and report["blocks"]
    allowed = {"label", "heading", "text", "code", "codefile", "outputfile"}
    for index, block in enumerate(report["blocks"]):
        assert block["type"] in allowed, f"Недопустимый тип блока: {block['type']} (индекс {index})"
        if block["type"] in ("codefile", "outputfile"):
            path = WORKSPACE / block["path"]
            assert path.is_file(), f"Файл не найден: {path}"
        if block["type"] == "label":
            assert block.get("label") and block.get("text"), f"Пустой блок {index}"
        if block["type"] in ("heading", "text", "code"):
            assert block.get("text"), f"Пустой блок {index}"


def main() -> int:
    """Собирает, сохраняет и повторно читает report.json."""
    report = {
        "practice": 10,
        "title": "ПРАКТИЧЕСКАЯ РАБОТА №10",
        "subtitle": "HTTP и REST API в Python: разработка клиент-серверного веб-приложения",
        "goal": (
            "Изучить устройство протокола HTTP, методы и коды состояния, принципы REST и получить практические "
            "навыки разработки клиент-серверного веб-приложения на Python: реализовать на Flask REST API для "
            "предметной области «Кинотеатр» (вариант 4) и HTTP-клиент к нему."
        ),
        "blocks": build_blocks(),
    }

    with REPORT_PATH.open("w", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2)

    with REPORT_PATH.open("r", encoding="utf-8") as file:
        loaded = json.load(file)

    validate(loaded)
    print("report.json создан:", REPORT_PATH)
    print("blocks:", len(loaded["blocks"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
