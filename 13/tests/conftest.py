"""Общие фикстуры тестов.

Тесты автоматически используют реальные MongoDB/Redis, если они доступны,
иначе — встроенные in-memory реализации (тот же интерфейс).
"""
from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.cache import RedisCache  # noqa: E402
from app.models import Director, Movie, Session  # noqa: E402
from app.mongodb import connect_mongo  # noqa: E402
from app.redis_client import connect_redis  # noqa: E402
from app.repository import MongoRepository  # noqa: E402
from app.service import MovieService  # noqa: E402

MONGO_URI = "mongodb://127.0.0.1:27017"
REDIS_URL = "redis://127.0.0.1:6379/0"


def make_movie(title: str = "Тестовый фильм", rating: float = 7.5, genre: str = "драма") -> Movie:
    """Собрать корректную модель фильма для тестов."""
    return Movie(
        title=title,
        director=Director(name="Тестовый Режиссёр", country="Россия"),
        year=2020,
        genres=[genre, "фантастика"],
        actors=["Актёр Один", "Актёр Два"],
        duration=120,
        rating=rating,
        poster="https://posters.local/test.jpg",
        sessions=[Session(date="2024-06-01", time="12:00", hall="Зал 1", price=300.0, format="2D")],
        status="showing",
    )


@pytest.fixture()
def repo() -> MongoRepository:
    """Чистый репозиторий в тестовой базе."""
    database, _mode, _error = connect_mongo(MONGO_URI, "cinema_test")
    repository = MongoRepository(database["movie"])
    repository.ensure_indexes()
    repository.delete_many({})
    return repository


@pytest.fixture()
def cache() -> RedisCache:
    """Чистый кэш в отдельном namespace."""
    client, _mode, _error = connect_redis(REDIS_URL)
    wrapper = RedisCache(client, namespace="cinema_test")
    wrapper.flush_namespace()
    return wrapper


@pytest.fixture()
def service(repo: MongoRepository, cache: RedisCache) -> MovieService:
    """Сервис с реальными/резервными хранилищами и TTL 60 секунд."""
    return MovieService(repo, cache, ttl=60)


@pytest.fixture()
def sample_movie() -> Movie:
    return make_movie()
