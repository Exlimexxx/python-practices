"""Тесты Redis-части: запись, чтение, TTL, структуры данных."""
from __future__ import annotations

import time


def test_redis_write_and_read(cache) -> None:
    """Запись в Redis и чтение из Redis (SET/GET)."""
    assert cache.set("answer", "42") is True
    assert cache.get("answer") == "42"


def test_redis_delete(cache) -> None:
    """Удаление ключа (DEL)."""
    cache.set("temp", "value")
    assert cache.delete("temp") == 1
    assert cache.get("temp") is None


def test_redis_ttl(cache) -> None:
    """TTL: ключ исчезает после истечения срока."""
    cache.set("short", "value", ttl=1)
    assert cache.ttl("short") in (0, 1)
    time.sleep(1.2)
    assert cache.get("short") is None
    assert cache.ttl("short") == -2


def test_redis_incr(cache) -> None:
    """Счётчик (INCR)."""
    assert cache.incr("counter") == 1
    assert cache.incr("counter", 4) == 5
    assert cache.get("counter") == 5


def test_redis_hash(cache) -> None:
    """Хэш (HSET/HGET/HGETALL)."""
    cache.hset("movie:meta", {"title": "Дюна", "year": 2021})
    assert cache.hget("movie:meta", "title") == "Дюна"
    assert cache.hgetall("movie:meta")["year"] == 2021


def test_redis_list(cache) -> None:
    """Список (RPUSH/LRANGE)."""
    cache.rpush("schedule", "12:00", "15:00", "18:00")
    assert cache.lrange("schedule", 0, 1) == ["12:00", "15:00"]
    assert cache.llen("schedule") == 3


def test_redis_set(cache) -> None:
    """Множество (SADD/SMEMBERS)."""
    cache.sadd("halls", "IMAX-1", "IMAX-2", "IMAX-2")
    assert cache.smembers("halls") == {"IMAX-1", "IMAX-2"}


def test_redis_sorted_set(cache) -> None:
    """Сортированное множество (ZADD/ZREVRANGE)."""
    cache.zadd("rating", {"Начало": 8.8, "Матрица": 8.7, "Побег": 9.3})
    top = cache.zrevrange("rating", 0, 0, withscores=True)
    assert top[0][0] == "Побег"
    assert cache.zscore("rating", "Матрица") == 8.7
