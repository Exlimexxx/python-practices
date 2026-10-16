"""Общие фикстуры pytest: временная БД, кэш и сервис.

БД создаётся в tmp_path, поэтому тесты не портят cinema.db.
"""
from __future__ import annotations

import sys
import uuid
from pathlib import Path

import pytest

# Делаем модули проекта (db, repository, service, cache, seed) импортируемыми.
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from cache import InMemoryCache  # noqa: E402
from db import connect  # noqa: E402
from seed import create_schema, seed_halls_and_screenings  # noqa: E402
from seed_movies import seed_movies  # noqa: E402
from service import CinemaService  # noqa: E402


@pytest.fixture()
def conn():
    """Соединение с полностью заполненной временной БД.

    Файл БД создаётся прямо в каталоге проекта (а не во вложенном каталоге
    и не в системном %TEMP%): в этой среде файловая песочница запрещает
    обход только что созданных каталогов, из-за чего SQLite не может
    открыть в них файл. После теста файл и его журналы удаляются.
    """
    db_path = BASE_DIR / f"_pytest_cinema_{uuid.uuid4().hex[:8]}.db"
    connection = connect(db_path)
    create_schema(connection)
    seed_movies(connection)
    seed_halls_and_screenings(connection)
    connection.commit()
    try:
        yield connection
    finally:
        connection.close()
        for suffix in ("", "-journal", "-wal", "-shm"):
            Path(str(db_path) + suffix).unlink(missing_ok=True)


@pytest.fixture()
def cache() -> InMemoryCache:
    return InMemoryCache()


@pytest.fixture()
def service(conn, cache) -> CinemaService:
    return CinemaService(conn, cache)
