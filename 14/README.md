# Лабораторная работа №14 — REST API на FastAPI (вариант 4)

 Предметная область: **Кинотеатр — фильмы**, ресурс `/movies`.

## Возможности

* CRUD: `POST`, `GET`, `PUT`, `PATCH`, `DELETE`;
* специальные операции: фильмы по жанру, поиск, статистика;
* фильтрация (`genre`, `min_rating`, `year`), сортировка (`sort`, `order`), пагинация (`limit`, `offset`);
* кэширование `GET /movies/{id}` в Redis с автоматическим fallback на in-memory;
* единый формат ошибок, коды 200/201/204/400/404/409/422/500;
* Swagger UI: `/docs`, ReDoc: `/redoc`, схема: `/openapi.json`.

## Структура

```
app/
├── main.py            # сборка приложения, middleware, обработчики ошибок
├── config.py          # настройки из переменных окружения
├── database.py        # engine, session, get_db
├── cache.py           # CacheBackend, RedisCache, InMemoryCache
├── exceptions.py      # собственные исключения и формат ошибок
├── logging_config.py  # настройка logging
├── routers/movies.py  # HTTP-слой
├── schemas/movie.py   # Pydantic-схемы
├── services/movie.py  # бизнес-логика + кэш
├── repositories/movie.py  # SQLAlchemy-запросы
└── models/movie.py    # ORM-модель
tests/test_api.py
```

## Запуск

```bash
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8014
# http://127.0.0.1:8014/docs
```

## Тесты

```bash
python -m pytest tests -v
```
