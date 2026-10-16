"""Демонстрация автоматического перехода на in-memory реализации.

Сценарий соответствует отклонению от методички: сервер Redis (а в общем случае
и MongoDB) может быть недоступен. Приложение не падает, а включает встроенное
документное хранилище и Redis-подобный кэш с TTL.
"""
from __future__ import annotations

from common import setup_logging, title

from app.cache import RedisCache
from app.mongodb import connect_mongo
from app.redis_client import connect_redis
from app.repository import MongoRepository
from app.seed import build_movies, seed
from app.service import MovieService

setup_logging()


def main() -> None:
    title("7. РЕЖИМ FALLBACK: НЕДОСТУПНЫЕ СЕРВЕРЫ MONGODB И REDIS")

    # Заведомо недоступные адреса
    database, mongo_mode, mongo_error = connect_mongo("mongodb://127.0.0.1:1", "cinema_offline", timeout_ms=300)
    print("MongoDB режим :", mongo_mode)
    print("MongoDB ошибка:", mongo_error)

    client, redis_mode, redis_error = connect_redis("redis://127.0.0.1:6399/0", socket_timeout=0.3)
    print("Redis режим   :", redis_mode)
    print("Redis ошибка  :", redis_error)

    repository = MongoRepository(database["movie"])
    created_indexes = repository.ensure_indexes()
    cache = RedisCache(client, namespace="cinema")
    service = MovieService(repository, cache, ttl=30)
    seeded = seed(build_movies(), repository)

    print("Тип хранилища :", type(database).__name__)
    print("Тип клиента   :", type(client).__name__)
    print("Индексы       :", created_indexes)
    print("Загружено документов:", seeded)
    assert mongo_mode == "memory" and redis_mode == "memory"

    title("FALLBACK: CRUD в in-memory хранилище")
    movie_id = repository.find({}, sort=[("rating", -1)], limit=1)[0]["_id"]
    print("Найден фильм      :", repository.get(movie_id).summary())
    print("Фильтров по жанру 'драма':", repository.count({"genres": "драма"}))
    top = repository.find({"rating": {"$gte": 8.8}}, projection={"title": 1, "rating": 1}, sort=[("rating", -1)], limit=3)
    print("Топ по рейтингу   :", top)
    service.update_movie(movie_id, {"rating": 9.5})
    print("После update      :", repository.get(movie_id).rating)

    title("FALLBACK: агрегация в in-memory хранилище")
    by_genre = repository.aggregate(
        [{"$unwind": "$genres"}, {"$group": {"_id": "$genres", "count": {"$sum": 1}}}, {"$sort": {"count": -1}}]
    )
    for row in by_genre[:5]:
        print("   ", row)

    title("FALLBACK: Redis-подобный кэш (SET/GET/TTL/INCR/HSET/ZADD)")
    cache.set("offline:key", "значение", ttl=30)
    print("SET/GET     :", cache.get("offline:key"))
    print("TTL         :", cache.ttl("offline:key"))
    print("INCR        :", cache.incr("offline:counter"), cache.incr("offline:counter"))
    cache.hset("offline:hash", {"a": 1, "b": 2})
    print("HGETALL     :", cache.hgetall("offline:hash"))
    cache.zadd("offline:zset", {"one": 1.0, "two": 2.0})
    print("ZREVRANGE   :", cache.zrevrange("offline:zset", 0, -1, withscores=True))

    title("FALLBACK: cache-aside в сервисе")
    service.clear_cache()
    first = service.get_movie(movie_id)
    second = service.get_movie(movie_id)
    print("Первый запрос (MISS):", first.title)
    print("Второй запрос (HIT):", second.title)
    print("Статистика кэша    :", service.stats)

    print("\nВсе операции выполнены без реальных серверов — приложение осталось работоспособным.")


if __name__ == "__main__":
    main()
