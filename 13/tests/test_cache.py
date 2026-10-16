"""Тесты cache-aside, инвалидации кэша и статистики сервиса."""
from __future__ import annotations

import time

from conftest import make_movie


def test_cache_aside_miss_then_hit(service) -> None:
    """Первый запрос — промах (MongoDB), второй — попадание (Redis)."""
    movie_id = service.add_movie(make_movie(title="Кэш-кейс"))
    service.clear_cache()

    first = service.get_movie(movie_id)
    assert first.title == "Кэш-кейс"
    assert service.stats["misses"] == 1
    assert service.cache.exists(service.movie_cache_key(movie_id)) == 1

    second = service.get_movie(movie_id)
    assert second.title == "Кэш-кейс"
    assert service.stats["hits"] == 1


def test_cache_ttl(service) -> None:
    """У кэшированного документа есть TTL не меньше 30 секунд."""
    movie_id = service.add_movie(make_movie(title="TTL"))
    service.get_movie(movie_id)
    ttl = service.cache.ttl(service.movie_cache_key(movie_id))
    assert service.ttl >= 30
    assert 0 < ttl <= service.ttl


def test_cache_invalidation_on_update(service) -> None:
    """Инвалидация кэша при изменении: следующий запрос идёт в MongoDB."""
    movie_id = service.add_movie(make_movie(title="Инвалидация", rating=5.0))
    service.get_movie(movie_id)
    key = service.movie_cache_key(movie_id)
    assert service.cache.exists(key) == 1

    service.update_movie(movie_id, {"rating": 8.0})
    assert service.cache.exists(key) == 0

    refreshed = service.get_movie(movie_id)
    assert refreshed.rating == 8.0
    assert service.stats["misses"] >= 2


def test_cache_invalidation_on_delete(service) -> None:
    """Инвалидация кэша при удалении."""
    movie_id = service.add_movie(make_movie(title="Удаление кэша"))
    service.get_movie(movie_id)
    key = service.movie_cache_key(movie_id)
    assert service.cache.exists(key) == 1

    service.delete_movie(movie_id)
    assert service.cache.exists(key) == 0


def test_movie_cached_value_matches_document(service) -> None:
    """Значение в кэше соответствует документу MongoDB."""
    movie_id = service.add_movie(make_movie(title="Сверка"))
    service.get_movie(movie_id)
    cached = service.cache.get_json(service.movie_cache_key(movie_id))
    assert cached["title"] == "Сверка"
    assert cached["_id"] == str(movie_id) or cached["_id"] == movie_id


def test_statistics(service) -> None:
    """Статистика собирается агрегацией по добавленным фильмам."""
    service.add_movie(make_movie(title="Стат1", rating=9.0, genre="драма"))
    service.add_movie(make_movie(title="Стат2", rating=7.0, genre="комедия"))
    stats = service.statistics()
    assert stats["total"] == 2
    assert stats["avg_rating"] == 8.0


def test_top_rated_uses_sorted_set(service) -> None:
    """Топ по рейтингу хранится в Sorted Set Redis."""
    service.add_movie(make_movie(title="Топ", rating=9.9))
    top = service.top_rated(1)
    assert len(top) == 1
    assert top[0][1] == 9.9
