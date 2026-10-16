"""Генерация итогового отчёта report.json.

Скрипт собирает описание работы, листинги файлов и ссылки на реальные
выводы запусков (demo/*.txt), затем проверяет результат через json.load.

Запуск:  python make_report.py
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
WORKSPACE = BASE_DIR.parent.parent          # ...\default-workspace
REPORT_PATH = BASE_DIR / "report.json"


def rel(path: Path) -> str:
    """Путь относительно рабочей директории workspace (в формате с /)."""
    return path.relative_to(WORKSPACE).as_posix()


def label(name: str, text: str) -> dict[str, Any]:
    return {"type": "label", "label": name, "text": text}


def heading(text: str) -> dict[str, Any]:
    return {"type": "heading", "text": text}


def text(body: str) -> dict[str, Any]:
    return {"type": "text", "text": body}


def code(caption: str, body: str) -> dict[str, Any]:
    return {"type": "code", "caption": caption, "text": body}


def codefile(caption: str, path: str) -> dict[str, Any]:
    return {"type": "codefile", "caption": caption, "path": path}


def outputfile(caption: str, path: str) -> dict[str, Any]:
    return {"type": "outputfile", "caption": caption, "path": path}


PROJECT_TREE = """work/practice11/
├── schema.sql              # DDL: 6 таблиц, PRIMARY/FOREIGN KEY, NOT NULL/UNIQUE/CHECK, 6 индексов
├── seed_movies.py          # каталог фильмов (12 фильмов и их жанры) + загрузка в БД
├── seed.py                 # полное наполнение: схема + фильмы + залы + 14 сеансов
├── queries.sql             # 19 SQL-запросов с маркерами -- @query
├── run_queries.py          # выполняет queries.sql и печатает результаты
├── db.py                   # подключение к SQLite, контекстный менеджер транзакций
├── repository.py           # репозитории Movie/Hall/Screening/Genre (параметризованные запросы)
├── service.py              # сервис: продажа билетов в транзакции, кэш рекомендаций
├── cache.py                # RedisCache (redis-py) или InMemoryCache (эмуляция Redis)
├── transaction_demo.py     # демонстрация COMMIT и ROLLBACK
├── cache_demo.py           # промах/попадание кэша, TTL, EXPIRE, INCR, DELETE
├── cdn_server.py           # CDN-сервер: Cache-Control public max-age=3600, ETag, Age, 304
├── origin_server.py        # сервер-источник: no-cache, no-store, must-revalidate
├── cdn_demo.py             # HTTP-сравнение CDN и origin (заголовки, размер, время)
├── static/
│   ├── posters/poster_1.svg, poster_2.svg, poster_3.svg   # 3 постера фильмов
│   ├── css/style.css       # оформление афиши
│   └── js/app.js           # клиентский скрипт рекомендаций
├── tests/
│   ├── conftest.py         # фикстуры: временная БД, кэш, сервис
│   ├── test_repository.py  # 11 тестов слоя данных
│   └── test_service.py     # 9 тестов бизнес-логики
├── pytest.ini
├── demo/                   # РЕАЛЬНЫЕ консольные выводы всех запусков
│   ├── seed.txt, queries.txt, transaction.txt
│   ├── cache.txt, cdn.txt, pytest.txt
│   └── cinema.db           # рабочая БД SQLite (создаётся seed.py)
└── make_report.py          # генерация этого отчёта"""

COMPARISON = """Критерий        | PostgreSQL / SQLite        | MongoDB                | Redis                    | CDN
----------------+----------------------------+------------------------+--------------------------+--------------------------
Назначение      | основные данные            | документы, каталог     | кэш и счётчики           | раздача статики
Модель данных   | таблицы, строки, схема     | документы BSON, гибко  | ключ-значение            | файлы и HTTP-метаданные
Структура       | жёсткая схема, связи 1:N/N:M| коллекции документов  | плоские пары key/value   | каталог файлов + URL
Хранение        | диск, журнал WAL, ACID     | диск, репликация       | оперативная память       | edge-серверы по всему миру
Запросы         | SQL: JOIN, GROUP BY, AVG   | find/aggregate, без JOIN| GET/SET/INCR/EXPIRE/TTL | GET по URL
Транзакции      | полные, ACID               | появились в 4.0        | условные (MULTI/EXEC)    | нет (только чтение)
Кэширование     | не кэш, источник истины    | не кэш                 | сам является кэшем       | Cache-Control, ETag, Age
Масштабирование | вертикальное + реплики     | шардирование           | кластер, репликация      | глобальная сеть узлов
Типичные данные | фильмы, сеансы, продажи    | отзывы, логи, события  | рекомендации, сессии     | постеры, CSS, JS
Когда выбирать  | связи и целостность данных | гибкая схема, объём    | скорость чтения, TTL     | скорость доставки файлов"""

CHECKLIST = """Требование методички                          | Как выполнено                                     | Где смотреть
---------------------------------------------+---------------------------------------------------+---------------------------
Минимум 3 таблицы                            | 6 таблиц                                          | schema.sql
Первичный ключ в каждой таблице              | PRIMARY KEY у всех 6 таблиц                       | schema.sql
Минимум 2 внешних ключа                      | 5 внешних ключей                                  | schema.sql
Связь 1:N                                    | movies -> screenings, halls -> screenings         | schema.sql
Связь N:M через промежуточную таблицу        | movies <-> genres через movie_genres              | schema.sql
PRIMARY KEY / FOREIGN KEY / NOT NULL /       | все виды ограничений + составной PK в movie_genres| schema.sql
UNIQUE / CHECK                               |                                                   |
Минимум 2 индекса                            | 6 индексов с пояснениями                          | schema.sql
Минимум 10 фильмов, 5 связанных записей      | 12 фильмов, 14 сеансов, 26 связей N:M             | seed_movies.py, seed.py
Минимум 15 SQL-запросов                      | 19 запросов                                       | queries.sql, run_queries.py
SELECT/WHERE/ORDER BY/JOIN/LEFT JOIN/        | запросы 1-19 покрывают все перечисленные пункты    | queries.sql
GROUP BY/HAVING/COUNT/AVG/SUM/подзапрос/     |                                                   |
несколько условий/несколько таблиц/          |                                                   |
INSERT/UPDATE/DELETE                         |                                                   |
Транзакция с COMMIT и ROLLBACK               | service.sell_ticket + transaction_demo.py         | service.py, transaction_demo.py
Repository + Service, параметризация         | repository.py, service.py, только «?» в запросах   | repository.py, service.py
pytest                                       | 20 тестов, все проходят                            | tests/
Cache-aside для рекомендаций, ключ, TTL 60 с | recommendations:movie:{id}, JSON, TTL 60          | service.py, cache.py
5 операций кэша                              | SET, GET, DELETE, EXPIRE, INCR (+TTL)             | cache.py, cache_demo.py
Промах/попадание/истечение TTL               | показаны в demo/cache.txt                         | cache_demo.py
3+ ресурса в static/                         | 3 постера SVG + style.css + app.js                | static/
CDN-сервер с Cache-Control и ETag            | cdn_server.py: public, max-age=3600, ETag, 304    | cdn_server.py
Origin без Cache-Control / с no-cache        | origin_server.py: no-cache, no-store              | origin_server.py
Сравнение CDN и origin                       | заголовки, размер и время                          | cdn_demo.py, demo/cdn.txt
Сравнительная таблица и объяснение           | разделы 11 и 12 отчёта                            | report.json"""

DEVIATIONS = (
    "ОТКЛОНЕНИЯ ОТ МЕТОДИЧКИ, ВЫЗВАННЫЕ СРЕДОЙ. В системе не установлены серверы PostgreSQL, "
    "MongoDB и Redis, поэтому: (1) реляционная часть выполнена на SQLite — методичка прямо "
    "разрешает SQLite в основной части работы; код написан на стандартном модуле sqlite3 и "
    "использует только параметризованные запросы, поэтому переносится на PostgreSQL заменой "
    "строки подключения и AUTOINCREMENT на SERIAL/IDENTITY. (2) Вместо Redis-сервера работает "
    "cache.py: при запуске класс create_cache() пытается подключиться к Redis и, если сервер "
    "недоступен (в demo/cache.txt видно предупреждение «Redis недоступен — включаю in-memory "
    "эмуляцию»), включает InMemoryCache — встроенную реализацию SET/GET/DELETE/EXPIRE/INCR/TTL. "
    "Класс RedisCache в том же файле содержит полноценный код для настоящего Redis "
    "(библиотека redis-py, decode_responses=True), включая set(..., ex=ttl), incrby и ttl; "
    "он включается автоматически, как только сервер 127.0.0.1:6379 становится доступен. "
    "(3) CDN имитируется двумя локальными HTTP-серверами на http.server (CDN и origin) — "
    "методичка допускает такую имитацию; это позволяет реально измерить заголовки, размер и "
    "время ответа."
)


def build_blocks() -> list[dict[str, Any]]:
    return [
        label("Ход работы (вариант 4)", (
            "Вариант 4, предметная область «Кинотеатр». Основная сущность — Movie (фильм). "
            "В нереляционное хранилище вынесены рекомендации фильмов, а на CDN — постеры. "
            "Работа состоит из трёх частей: реляционная база со связями 1:N и N:M на SQLite; "
            "кэш-слой рекомендаций по схеме cache-aside с TTL 60 секунд; имитация CDN, "
            "раздающая постеры с заголовками кэширования."
        )),
        heading("1. Постановка задачи и вариант"),
        text(
            "Предметная область — кинотеатр. Основные данные (фильмы, залы, сеансы, жанры, "
            "продажи билетов) хранятся в реляционной БД: для них важны целостность, связи и "
            "транзакции при продаже билетов. Вспомогательные, часто запрашиваемые и при этом "
            "легко пересчитываемые данные — рекомендации фильмов — вынесены в кэш с временем "
            "жизни 60 секунд. Тяжёлый и статичный контент — постеры фильмов, CSS и JS — "
            "раздаётся через CDN, а не сервером приложения."
        ),
        text(DEVIATIONS),
        heading("2. Структура проекта"),
        code("Структура проекта", PROJECT_TREE),
        heading("3. Реляционная часть: схема базы данных"),
        text(
            "Схема содержит 6 таблиц. movies — основная сущность (id, title, duration, rating, "
            "poster_path). halls — кинозалы (id, name, capacity). screenings — сеансы; это связь "
            "1:N сразу с двумя таблицами: movie_id ссылается на movies, hall_id — на halls. "
            "genres — справочник жанров, а movie_genres — промежуточная таблица связи N:M "
            "«фильмы — жанры» с составным первичным ключом (movie_id, genre_id). ticket_sales "
            "хранит факты продажи билетов и ссылается на screenings."
        ),
        text(
            "Ограничения целостности: PRIMARY KEY у всех шести таблиц; пять FOREIGN KEY "
            "(screenings.movie_id, screenings.hall_id, movie_genres.movie_id, "
            "movie_genres.genre_id, ticket_sales.screening_id); NOT NULL на обязательных полях; "
            "UNIQUE на movies.title, halls.name и на паре (hall_id, start_time) — в одном зале "
            "не может быть двух сеансов одновременно; CHECK на положительную длительность, "
            "рейтинг в диапазоне 0..10, положительные цену, количество билетов и вместимость."
        ),
        text(
            "Шесть индексов созданы под конкретные запросы: idx_screenings_movie — для JOIN "
            "movies<->screenings и выборки сеансов фильма; idx_screenings_start — для афиши "
            "(WHERE/ORDER BY по времени); idx_screenings_hall — для отчётов по залам; "
            "idx_movies_rating — для топа по рейтингу; idx_movie_genres_genre — для подбора по "
            "жанру и построения рекомендаций; idx_sales_screening — для подсчёта выручки и "
            "истории продаж."
        ),
        codefile("schema.sql", "work/practice11/schema.sql"),
        heading("4. Первичное наполнение базы данных"),
        text(
            "seed_movies.py содержит 12 фильмов (требуется минимум 10) и связи с 7 жанрами: "
            "26 записей в movie_genres. seed.py создаёт схему, загружает фильмы, добавляет "
            "4 зала и 14 сеансов (требуется минимум 5 связанных записей). Все вставки выполняются "
            "параметризованными запросами executemany."
        ),
        codefile("seed_movies.py", "work/practice11/seed_movies.py"),
        codefile("seed.py", "work/practice11/seed.py"),
        outputfile("Результат выполнения: python seed.py", "work/practice11/demo/seed.txt"),
        heading("5. SQL-запросы (19 штук)"),
        text(
            "Файл queries.sql содержит 19 запросов, разделённых маркерами «-- @query». Покрытие "
            "требований: SELECT и WHERE (1, 2), ORDER BY с LIMIT (3), JOIN связи 1:N (4), "
            "LEFT JOIN (5 — фильмы без сеансов), GROUP BY (6), HAVING (7 — жанры у двух и более "
            "фильмов), COUNT и SUM (8), AVG (9), SUM с группировкой и выручкой (10), скалярный "
            "подзапрос (11), подзапрос NOT EXISTS (12), несколько условий в WHERE (13), JOIN "
            "пяти таблиц (14), связь N:M с GROUP_CONCAT (15), INSERT (16), UPDATE (17), DELETE "
            "(18) и контрольный SELECT после DML (19). Запросы 16-18 изменяют данные и "
            "завершаются так, чтобы база вернулась в исходное состояние."
        ),
        codefile("queries.sql", "work/practice11/queries.sql"),
        codefile("run_queries.py", "work/practice11/run_queries.py"),
        outputfile("Результат выполнения: python run_queries.py", "work/practice11/demo/queries.txt"),
        heading("6. Транзакция продажи билета"),
        text(
            "Сервис CinemaService.sell_ticket выполняет одну транзакцию из трёх шагов: проверка "
            "сеанса и числа свободных мест, вставка записи в ticket_sales, увеличение счётчика "
            "tickets_sold. Контекстный менеджер db.transaction() выполняет BEGIN, затем COMMIT "
            "при успехе; любое исключение приводит к ROLLBACK, поэтому частичных изменений не "
            "остаётся. Если мест не хватает, возбуждается собственное исключение "
            "SeatUnavailableError — оно наследуется от CinemaError. В демонстрации сначала "
            "показана успешная продажа с COMMIT, затем попытка продать 100 билетов при 27 "
            "свободных местах с ROLLBACK и проверкой, что ни счётчик, ни таблица продаж не "
            "изменились, и снова успешная продажа."
        ),
        codefile("transaction_demo.py", "work/practice11/transaction_demo.py"),
        outputfile("Результат выполнения: python transaction_demo.py", "work/practice11/demo/transaction.txt"),
        heading("7. Интеграция с Python: Repository + Service и защита от SQL-инъекций"),
        text(
            "Код разделён на слои: db.py отвечает за соединение и транзакции, repository.py — за "
            "доступ к данным (классы MovieRepository, HallRepository, ScreeningRepository, "
            "GenreRepository), service.py — за бизнес-логику (CinemaService), cache.py — за "
            "кэширование. Все SQL-запросы выполняются только через параметры-заполнители «?»: "
            "значения передаются отдельным кортежем и никогда не склеиваются со строкой запроса."
        ),
        text(
            "SQL-инъекция — это атака, при которой ввод пользователя попадает в текст SQL-запроса "
            "и меняет его смысл. Пример: если бы поиск фильма строился как "
            "\"SELECT * FROM movies WHERE title = '\" + user_input + \"'\", то ввод "
            "«' OR '1'='1» вернул бы всю таблицу, а ввод «Начало'; DROP TABLE movies;--» мог "
            "уничтожить таблицу. Параметризация решает проблему: драйвер передаёт значение "
            "отдельно от SQL-кода, и СУБД трактует его исключительно как данные — кавычки и "
            "операторы внутри строки теряют синтаксический смысл. Это проверяется тестом "
            "test_search_uses_parameter_and_blocks_sql_injection: поиск по строке "
            "«' OR '1'='1» возвращает пустой список, а таблица остаётся на месте. Дополнительно "
            "ограничения CHECK, UNIQUE и FOREIGN KEY проверяются тестами: драйвер возбуждает "
            "sqlite3.IntegrityError."
        ),
        codefile("db.py", "work/practice11/db.py"),
        codefile("repository.py", "work/practice11/repository.py"),
        codefile("service.py", "work/practice11/service.py"),
        heading("8. Тестирование (pytest)"),
        text(
            "Написано 20 тестов. test_repository.py проверяет наполнение БД (не менее 10 "
            "фильмов), получение сущности, защиту от SQL-инъекции, срабатывание ограничений "
            "UNIQUE, CHECK и FOREIGN KEY, связь N:M, подсчёт свободных мест через JOIN и "
            "обновление счётчика продаж. test_service.py проверяет транзакцию (успешный COMMIT, "
            "ROLLBACK при нехватке мест, отсутствие изменений после отката), схему cache-aside "
            "(промах, попадание, инвалидация), JSON-сериализацию кириллицы и поведение кэша "
            "(TTL, EXPIRE, INCR, DELETE). Тесты используют временную БД в каталоге проекта, "
            "поэтому не портят cinema.db."
        ),
        codefile("tests/conftest.py", "work/practice11/tests/conftest.py"),
        codefile("tests/test_repository.py", "work/practice11/tests/test_repository.py"),
        codefile("tests/test_service.py", "work/practice11/tests/test_service.py"),
        outputfile("Результат выполнения: python -m pytest", "work/practice11/demo/pytest.txt"),
        heading("9. NoSQL-часть: кэш рекомендаций (cache-aside)"),
        text(
            "Рекомендации строятся SQL-запросом: для фильма-источника ищутся фильмы с общими "
            "жанрами, сортировка — по числу общих жанров и затем по рейтингу. Схема cache-aside "
            "реализована в CinemaService.recommendations: сначала выполняется GET по ключу "
            "recommendations:movie:{id}; при промахе данные читаются из SQLite и кладутся в кэш "
            "командой SET с TTL 60 секунд в виде JSON (ensure_ascii=False, поэтому кириллица "
            "хранится читаемо); при попадании ответ берётся из кэша, а SQLite не опрашивается. "
            "Инвалидация — метод invalidate_recommendations, удаляющий ключ, чтобы данные "
            "пересчитались. Всего продемонстрировано 6 операций: SET, GET, DELETE, EXPIRE, INCR "
            "и TTL, а также промах, попадание и истечение TTL."
        ),
        text(
            "Зачем нужен TTL и почему нельзя кэшировать изменяемые данные вечно: кэш — это копия, "
            "она устаревает, как только меняются исходные данные. Если рейтинг фильма изменится "
            "или появятся новые фильмы того же жанра, бессрочная копия будет отдавать устаревшие "
            "рекомендации. TTL ограничивает время жизни копии: через 60 секунд ключ исчезает и "
            "данные пересчитываются. Cache invalidation — управляемое удаление или обновление "
            "ключей при изменении данных; это самая сложная часть кэширования, поэтому "
            "применяются оба механизма: активный (DELETE при изменении, "
            "invalidate_recommendations) и пассивный (TTL). Кэшировать рекомендации выгодно, "
            "потому что их расчёт — тяжёлый запрос с самосоединением таблицы movie_genres, "
            "GROUP BY и сортировкой, а запрашиваются они часто (для каждого открытия карточки "
            "фильма), при этом небольшие расхождения в течение минуты не критичны. В демонстрации "
            "попадание в кэш выполняется заметно быстрее промаха, а Redis дополнительно снимает "
            "нагрузку с основной БД."
        ),
        codefile("cache.py", "work/practice11/cache.py"),
        codefile("cache_demo.py", "work/practice11/cache_demo.py"),
        outputfile("Результат выполнения: python cache_demo.py", "work/practice11/demo/cache.txt"),
        heading("10. CDN: раздача постеров фильмов"),
        text(
            "Папка static/ содержит 5 ресурсов: три постера в формате SVG, style.css и app.js. "
            "cdn_server.py — это имитация edge-узла CDN: он отдаёт статику с заголовком "
            "Cache-Control: public, max-age=3600, добавляет ETag, заголовок Age и поддерживает "
            "условные запросы If-None-Match, отвечая 304 Not Modified без тела. origin_server.py "
            "отдаёт те же файлы, но с Cache-Control: no-cache, no-store, must-revalidate, "
            "Pragma: no-cache и Expires: 0 — кэшировать такие ответы нельзя. cdn_demo.py "
            "поднимает оба сервера, выполняет HTTP-запросы и печатает URL, статус, заголовки "
            "Cache-Control, Content-Length, Content-Type, ETag, Age, размер ответа и время "
            "ответа, а затем сравнивает первый и повторный запросы."
        ),
        codefile("cdn_server.py", "work/practice11/cdn_server.py"),
        codefile("origin_server.py", "work/practice11/origin_server.py"),
        codefile("cdn_demo.py", "work/practice11/cdn_demo.py"),
        outputfile("Результат выполнения: python cdn_demo.py", "work/practice11/demo/cdn.txt"),
        heading("11. Сравнительная таблица PostgreSQL / MongoDB / Redis / CDN"),
        code("Сравнение хранилищ", COMPARISON),
        heading("12. Архитектурное объяснение: почему данные хранятся именно здесь"),
        text(
            "ПОЧЕМУ ОСНОВНЫЕ ДАННЫЕ — В РЕЛЯЦИОННОЙ БД (в методичке PostgreSQL, здесь SQLite). "
            "Фильмы, залы, сеансы, жанры и продажи билетов связаны между собой и требуют "
            "целостности: нельзя продать билет на несуществующий сеанс, нельзя дважды занять один "
            "зал в одно время, нельзя удалить фильм, оставив висящие сеансы. Именно для этого "
            "нужны внешние ключи, ограничения и транзакции ACID, а связь N:M и отчёты по выручке "
            "естественно выражаются через JOIN, GROUP BY и HAVING. Поэтому основное хранилище — "
            "реляционное, и оно является источником истины."
        ),
        text(
            "ПОЧЕМУ РЕКОМЕНДАЦИИ — В КЭШЕ (Redis). Рекомендации не являются исходными данными: "
            "их всегда можно пересчитать из реляционной БД. При этом запрос дорогой (самосоединение "
            "movie_genres, группировка, сортировка), а вызывается он часто. Redis хранит пары "
            "ключ-значение в памяти, поэтому GET выполняется за микросекунды, а встроенный TTL "
            "автоматически удаляет устаревшие ключи. Дополнительные плюсы — разгрузка основной "
            "БД и единый кэш для нескольких экземпляров приложения (в отличие от кэша в памяти "
            "процесса). Ключ recommendations:movie:{id} и TTL 60 секунд дают компромисс между "
            "свежестью и скоростью."
        ),
        text(
            "ПОЧЕМУ ПОСТЕРЫ — НА CDN. Постеры, CSS и JS — это статические файлы, которые не "
            "меняются от запроса к запросу, но занимают много трафика и нужны всем пользователям "
            "одновременно. Отдавать их сервером приложения расточительно: он тратил бы "
            "соединения и пропускную способность на файлы, не связанные с бизнес-логикой. CDN "
            "хранит копии на географически распределённых edge-серверах рядом с пользователем, "
            "снижая задержку и нагрузку на origin. Заголовок Cache-Control: public, max-age=3600 "
            "разрешает браузеру и промежуточным кэшам хранить постер час, а ETag позволяет "
            "проверить актуальность и получить 304 Not Modified вместо повторной передачи файла. "
            "Так как постеры неизменяемы, их можно кэшировать долго, и именно поэтому в "
            "movies.poster_path хранится относительный путь к ресурсу CDN, а не сам файл: "
            "в БД держат ссылку, а байты — на CDN."
        ),
        heading("13. Соответствие требованиям методички"),
        code("Чек-лист требований", CHECKLIST),
        label("Вывод", (
            "В ходе работы спроектирована и реализована гибридная система хранения данных для "
            "предметной области «Кинотеатр». Реляционная часть выполнена на SQLite: 6 таблиц с "
            "первичными и пятью внешними ключами, связями 1:N и N:M, ограничениями NOT NULL, "
            "UNIQUE и CHECK и 6 индексами; база наполнена 12 фильмами, 4 залами, 7 жанрами, "
            "26 связями N:M и 14 сеансами. Написаны 19 SQL-запросов, покрывающих все требуемые "
            "конструкции, и скрипт run_queries.py, который их выполняет и печатает результаты. "
            "Продажа билетов реализована как транзакция с COMMIT и ROLLBACK и продемонстрирована "
            "на успешном и неуспешном сценариях. Код разделён на слои Repository и Service и "
            "использует исключительно параметризованные запросы, что исключает SQL-инъекции; "
            "20 тестов pytest проходят. Нереляционная часть выполнена как кэш рекомендаций по "
            "схеме cache-aside с ключом recommendations:movie:{id}, JSON-сериализацией и TTL "
            "60 секунд; показаны промах, попадание, истечение TTL и операции SET, GET, DELETE, "
            "EXPIRE, INCR. Статический контент (3 постера, CSS, JS) раздаётся имитацией CDN с "
            "заголовками Cache-Control: public, max-age=3600, ETag и Age и ответом 304 на "
            "условный запрос, а origin-сервер запрещает кэширование; сравнение зафиксировано "
            "измерениями. Из-за отсутствия в системе серверов PostgreSQL и Redis реляционная "
            "часть выполнена на разрешённом методичкой SQLite, а кэш при недоступности Redis "
            "автоматически переключается на встроенную in-memory эмуляцию; код реального Redis "
            "приведён в cache.py и включается без изменений при появлении сервера. Все выводы в "
            "demo/*.txt получены реальными запусками программ."
        )),
    ]


def validate(blocks: list[dict[str, Any]]) -> None:
    """Проверяет, что все указанные в блоках файлы существуют."""
    problems: list[str] = []
    for block in blocks:
        if block["type"] in {"codefile", "outputfile"}:
            path = WORKSPACE / block["path"]
            if not path.exists():
                problems.append(block["path"])
    if problems:
        raise SystemExit("Не найдены файлы, указанные в отчёте: " + ", ".join(problems))


def main() -> int:
    blocks = build_blocks()
    validate(blocks)
    report = {
        "practice": 11,
        "title": "ПРАКТИЧЕСКАЯ РАБОТА №11",
        "subtitle": "Реляционные и нереляционные базы данных. Хранение данных и использование CDN",
        "goal": (
            "Освоить реляционное и нереляционное хранение данных и организацию раздачи "
            "статического контента через CDN на примере предметной области «Кинотеатр»: "
            "спроектировать схему БД со связями 1:N и N:M и ограничениями целостности, "
            "реализовать слой доступа к данным с параметризованными запросами и транзакциями, "
            "кэшировать рекомендации фильмов по схеме cache-aside и сравнить раздачу постеров "
            "через CDN и сервер-источник."
        ),
        "blocks": blocks,
    }

    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Проверка: файл должен читаться обратно без потерь.
    loaded = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    kinds: dict[str, int] = {}
    for block in loaded["blocks"]:
        kinds[block["type"]] = kinds.get(block["type"], 0) + 1

    print("report.json успешно создан и проверен через json.load")
    print("  practice :", loaded["practice"])
    print("  title    :", loaded["title"])
    print("  subtitle :", loaded["subtitle"])
    print("  блоков   :", len(loaded["blocks"]))
    for kind, count in sorted(kinds.items()):
        print(f"    {kind:11s}: {count}")
    print("  файл     :", REPORT_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
