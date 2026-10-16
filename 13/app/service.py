"""MovieService — бизнес-логика приложения «Кинотеатр — фильмы».

Сервис связывает MongoRepository и RedisCache:
* реализует паттерн cache-aside (проверка кэша -> MongoDB -> запись в кэш);
* инвалидирует кэш при изменении и удалении документов;
* ведёт рейтинг фильмов и счётчик просмотров в Redis;
* собирает статистику через aggregation pipeline MongoDB;
* измеряет производительность MongoDB и Redis.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Sequence

from .cache import RedisCache
from .errors import NotFoundError, ValidationError
from .models import Movie
from .repository import MongoRepository, normalize_id

logger = logging.getLogger(__name__)

#: Ключ сортированного множества с рейтингом фильмов.
RATING_ZSET = "rating"
#: Ключ сортированного множества с популярностью (число просмотров).
POPULAR_ZSET = "popular"
#: Ключ счётчика просмотров.
VIEWS_PREFIX = "views"
#: Ключ списка последних просмотренных фильмов.
RECENT_LIST = "recent"


class MovieService:
    """Бизнес-логика: CRUD, поиск, статистика и кэширование."""

    def __init__(self, repository: MongoRepository, cache: RedisCache, ttl: int = 60) -> None:
        self.repository = repository
        self.cache = cache
        self.ttl = max(1, int(ttl))
        self.stats = {"hits": 0, "misses": 0}

    # --------------------------------------------------------------- кэш
    def movie_cache_key(self, movie_id: Any) -> str:
        return self.cache.key("movie", movie_id)

    def _store_in_cache(self, movie: Movie) -> None:
        self.cache.set_json(self.movie_cache_key(movie.id), movie.to_document(), ttl=self.ttl)

    def invalidate_movie(self, movie_id: Any) -> int:
        """Инвалидировать кэш конкретного фильма (DEL)."""
        removed = self.cache.delete(self.movie_cache_key(movie_id))
        logger.info("Инвалидация кэша movie:%s -> удалено ключей: %s", movie_id, removed)
        return removed

    # ----------------------------------------------------------------- CRUD
    def add_movie(self, movie: Movie) -> Any:
        """Create: добавить фильм, обновить рейтинг в Redis."""
        movie.validate()
        movie_id = self.repository.create(movie)
        movie.id = movie_id
        key = self.movie_cache_key(movie_id)
        self.cache.zadd(self.cache.key(RATING_ZSET), {str(movie_id): movie.rating})
        self.cache.hset(
            self.cache.key("movie", movie_id, "meta"),
            {"title": movie.title, "year": movie.year, "rating": movie.rating},
        )
        logger.info("Фильм добавлен и записан в Redis: %s", key)
        return movie_id

    def get_movie(self, movie_id: Any, use_cache: bool = True) -> Movie:
        """Read одного объекта по схеме cache-aside."""
        key = self.movie_cache_key(movie_id)
        if use_cache:
            cached = self.cache.get_json(key)
            if cached is not None:
                self.stats["hits"] += 1
                logger.info("CACHE HIT  %s (TTL=%s c)", key, self.cache.ttl(key))
                movie = Movie.from_document(cached)
                self._register_view(movie_id)
                return movie
            self.stats["misses"] += 1
            logger.info("CACHE MISS %s -> обращение к MongoDB", key)
        else:
            logger.info("CACHE BYPASS %s -> обращение к MongoDB", key)

        document = self.repository.get_document(movie_id)  # NotFoundError при отсутствии
        movie = Movie.from_document(document)
        if use_cache:
            self._store_in_cache(movie)
            logger.info("Данные помещены в Redis: %s (TTL=%s c)", key, self.ttl)
        self._register_view(movie_id)
        return movie

    def _register_view(self, movie_id: Any) -> None:
        """Учёт просмотров: INCR + ZADD + RPUSH/LTRIM (Redis)."""
        views = self.cache.incr(self.cache.key(VIEWS_PREFIX, movie_id))
        self.cache.zadd(self.cache.key(POPULAR_ZSET), {str(movie_id): float(views)})
        self.cache.lpush(self.cache.key(RECENT_LIST), str(movie_id))
        self.cache.ltrim(self.cache.key(RECENT_LIST), 0, 9)

    def list_movies(self, limit: int = 0, skip: int = 0, sort: Any = None) -> list[Movie]:
        """Read списка объектов."""
        return self.repository.find_movies({}, sort=sort or [("rating", -1)], limit=limit, skip=skip)

    def search(
        self,
        query: dict[str, Any],
        projection: dict[str, Any] | None = None,
        sort: Any = None,
        limit: int = 0,
    ) -> list[dict[str, Any]]:
        """Read объектов по условию (с проекцией)."""
        return self.repository.find(query, projection=projection, sort=sort, limit=limit)

    def update_movie(self, movie_id: Any, changes: dict[str, Any]) -> Movie:
        """Update: изменить поля и инвалидировать кэш."""
        if not changes:
            raise ValidationError("Не указаны поля для изменения")
        key = normalize_id(movie_id)
        self.repository.get_document(key)  # проверка существования -> NotFoundError
        self.repository.update(key, changes)
        self.invalidate_movie(key)
        movie = self.repository.get(key)
        if "rating" in changes:
            self.cache.zadd(self.cache.key(RATING_ZSET), {str(key): float(changes["rating"])})
        return movie

    def delete_movie(self, movie_id: Any) -> bool:
        """Delete: удалить документ и инвалидировать кэш и рейтинги."""
        key = normalize_id(movie_id)
        deleted = self.repository.delete(key)
        if not deleted:
            raise NotFoundError(f"Фильм с _id={movie_id!r} не найден")
        self.invalidate_movie(key)
        self.cache.zrem(self.cache.key(RATING_ZSET), str(key))
        self.cache.zrem(self.cache.key(POPULAR_ZSET), str(key))
        self.cache.delete(self.cache.key(VIEWS_PREFIX, key))
        self.cache.delete(self.cache.key("movie", key, "meta"))
        return deleted

    # ------------------------------------------------------------ рейтинги
    def top_rated(self, count: int = 5) -> list[tuple[str, float]]:
        """ZREVRANGE: топ фильмов по рейтингу (из Redis)."""
        return list(self.cache.zrevrange(self.cache.key(RATING_ZSET), 0, count - 1, withscores=True))

    def popular(self, count: int = 5) -> list[tuple[str, float]]:
        """ZREVRANGE: самые популярные фильмы по числу просмотров."""
        return list(self.cache.zrevrange(self.cache.key(POPULAR_ZSET), 0, count - 1, withscores=True))

    def recent(self, count: int = 5) -> list[str]:
        """LRANGE: последние просмотренные фильмы."""
        return list(self.cache.lrange(self.cache.key(RECENT_LIST), 0, count - 1))

    # ---------------------------------------------------------- статистика
    def statistics(self) -> dict[str, Any]:
        """Статистика через aggregation pipeline MongoDB."""
        total = self.repository.count({})
        avg_rating = self.repository.aggregate(
            [{"$group": {"_id": None, "avg_rating": {"$avg": "$rating"}, "max_rating": {"$max": "$rating"}}}]
        )
        by_status = self.repository.aggregate(
            [{"$group": {"_id": "$status", "count": {"$sum": 1}}}, {"$sort": {"count": -1}}]
        )
        by_genre = self.repository.aggregate(
            [
                {"$unwind": "$genres"},
                {"$group": {"_id": "$genres", "count": {"$sum": 1}, "avg_rating": {"$avg": "$rating"}}},
                {"$sort": {"count": -1, "avg_rating": -1}},
            ]
        )
        by_director = self.repository.aggregate(
            [
                {"$group": {"_id": "$director.name", "count": {"$sum": 1}, "avg_rating": {"$avg": "$rating"}}},
                {"$sort": {"count": -1, "avg_rating": -1}},
                {"$limit": 5},
            ]
        )
        return {
            "total": total,
            "avg_rating": avg_rating[0]["avg_rating"] if avg_rating else None,
            "max_rating": avg_rating[0]["max_rating"] if avg_rating else None,
            "by_status": by_status,
            "by_genre": by_genre,
            "top_directors": by_director,
        }

    # -------------------------------------------------------------- кэш
    def cache_status(self) -> dict[str, Any]:
        """Состояние кэша: ключи, их типы и TTL."""
        keys = self.cache.keys(self.cache.namespace + ":*")
        entries = []
        for key in keys:
            entries.append({"key": key, "type": self.cache.type(key), "ttl": self.cache.ttl(key)})
        return {
            "namespace": self.cache.namespace,
            "keys_total": len(keys),
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "entries": entries,
        }

    def clear_cache(self) -> int:
        """Очистить весь кэш приложения (key namespace:*)."""
        removed = self.cache.flush_namespace()
        self.stats = {"hits": 0, "misses": 0}
        logger.info("Кэш очищен, удалено ключей: %s", removed)
        return removed

    # -------------------------------------------------------- производительность
    def benchmark(self, sizes: Sequence[int] = (100, 1000, 10000)) -> list[dict[str, Any]]:
        """Сравнить прямое чтение из MongoDB и чтение из кэша Redis."""
        movies = self.repository.find({}, limit=1)
        if not movies:
            raise ValidationError("Нет документов для теста производительности")
        movie_id = movies[0]["_id"]

        # прогреваем кэш
        movie = self.repository.get(movie_id)
        self.cache.set_json(self.movie_cache_key(movie_id), movie.to_document(), ttl=self.ttl)

        results: list[dict[str, Any]] = []
        for size in sizes:
            start = time.perf_counter()
            for _ in range(size):
                self.repository.get_document(movie_id)
            mongo_total = time.perf_counter() - start

            start = time.perf_counter()
            key = self.movie_cache_key(movie_id)
            for _ in range(size):
                self.cache.get_json(key)
            redis_total = time.perf_counter() - start

            results.append(
                {
                    "requests": int(size),
                    "mongo_total_sec": round(mongo_total, 6),
                    "mongo_avg_ms": round(mongo_total / size * 1000, 6),
                    "redis_total_sec": round(redis_total, 6),
                    "redis_avg_ms": round(redis_total / size * 1000, 6),
                    "speedup": round(mongo_total / redis_total, 2) if redis_total else None,
                }
            )
        return results
