"""Общие утилиты демонстрационных сценариев."""
from __future__ import annotations

import json
import logging
import pathlib
import sys
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.cache import RedisCache  # noqa: E402
from app.mongodb import connect_mongo  # noqa: E402
from app.redis_client import connect_redis  # noqa: E402
from app.repository import MongoRepository  # noqa: E402
from app.seed import build_movies, seed  # noqa: E402
from app.service import MovieService  # noqa: E402

MONGO_URI = "mongodb://127.0.0.1:27017"
REDIS_URL = "redis://127.0.0.1:6379/0"


def setup_logging() -> None:
    """Логировать в stdout, чтобы весь вывод попал в файл демонстрации."""
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stdout,
        format="%(levelname)-8s %(name)-18s | %(message)s",
        force=True,
    )


def title(text: str) -> None:
    """Печать заголовка раздела."""
    print()
    print("=" * 78)
    print(text)
    print("=" * 78)


def show_json(data: Any) -> None:
    """Печать объекта в JSON с поддержкой ObjectId."""
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str))


def make_service(
    mongo_uri: str = MONGO_URI,
    redis_url: str = REDIS_URL,
    ttl: int = 60,
    reset: bool = True,
    with_seed: bool = True,
) -> tuple[MovieService, dict[str, Any]]:
    """Собрать сервис; при reset=True коллекция очищается и засевается заново."""
    database, mongo_mode, mongo_error = connect_mongo(mongo_uri, "cinema")
    repository = MongoRepository(database["movie"])
    repository.ensure_indexes()
    if reset:
        repository.delete_many({})
    client, redis_mode, redis_error = connect_redis(redis_url)
    cache = RedisCache(client, namespace="cinema")
    service = MovieService(repository, cache, ttl=ttl)
    seeded = seed(build_movies(), repository) if with_seed else 0
    info = {
        "mongo_mode": mongo_mode,
        "mongo_error": mongo_error,
        "redis_mode": redis_mode,
        "redis_error": redis_error,
        "documents": repository.count({}),
        "seeded": seeded,
    }
    return service, info


def print_backends(info: dict[str, Any]) -> None:
    """Сообщить, какие хранилища реально используются."""
    print("MongoDB :", "реальный сервер" if info["mongo_mode"] == "mongodb" else "in-memory fallback")
    if info["mongo_error"]:
        print("          причина: " + str(info["mongo_error"]))
    print("Redis   :", "реальный сервер" if info["redis_mode"] == "redis" else "in-memory fallback")
    if info["redis_error"]:
        print("          причина: " + str(info["redis_error"]))
    print("Документов movie:", info["documents"])
