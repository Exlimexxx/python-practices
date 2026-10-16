"""Кэш: Redis с автоматическим fallback на in-memory (п. 17, 33, 34 методички)."""
from __future__ import annotations

import abc
import json
import logging
import time
from typing import Any

from .config import get_settings

logger = logging.getLogger(__name__)


class CacheBackend(abc.ABC):
    """Абстрактный интерфейс кэша (RFC: get/set/delete/clear)."""

    @abc.abstractmethod
    async def get(self, key: str) -> Any | None: ...

    @abc.abstractmethod
    async def set(self, key: str, value: Any, ttl: int | None = None) -> None: ...

    @abc.abstractmethod
    async def delete(self, key: str) -> None: ...

    @abc.abstractmethod
    async def clear(self) -> None: ...

    @abc.abstractmethod
    async def close(self) -> None: ...


class InMemoryCache(CacheBackend):
    """Простой словарный кэш с TTL. Используется как fallback без Redis."""

    def __init__(self, ttl: int = 60) -> None:
        self._ttl = ttl
        self._store: dict[str, tuple[float, Any]] = {}
        self.hits = 0
        self.misses = 0

    async def get(self, key: str) -> Any | None:
        item = self._store.get(key)
        if item is None:
            self.misses += 1
            return None
        expires_at, value = item
        if expires_at < time.monotonic():
            # запись устарела — удаляем и считаем промахом
            self._store.pop(key, None)
            self.misses += 1
            return None
        self.hits += 1
        return value

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        ttl = self._ttl if ttl is None else ttl
        self._store[key] = (time.monotonic() + ttl, value)

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def clear(self) -> None:
        self._store.clear()

    async def close(self) -> None:
        self._store.clear()

    def reset_stats(self) -> None:
        self.hits = 0
        self.misses = 0

    @property
    def size(self) -> int:
        return len(self._store)


class RedisCache(CacheBackend):
    """Кэш на базе Redis (redis.asyncio)."""

    def __init__(self, client: Any, ttl: int = 60) -> None:
        self._client = client
        self._ttl = ttl

    async def get(self, key: str) -> Any | None:
        raw = await self._client.get(key)
        if raw is None:
            return None
        return json.loads(raw)

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        ttl = self._ttl if ttl is None else ttl
        await self._client.set(key, json.dumps(value, ensure_ascii=False), ex=ttl)

    async def delete(self, key: str) -> None:
        await self._client.delete(key)

    async def clear(self) -> None:
        await self._client.flushdb()

    async def close(self) -> None:
        await self._client.aclose()


_cache: CacheBackend | None = None
_cache_kind: str = "none"


async def init_cache() -> CacheBackend:
    """Инициализирует кэш: пытается поднять Redis, иначе переходит на память."""
    global _cache, _cache_kind
    settings = get_settings()

    if settings.cache_backend == "memory":
        _cache = InMemoryCache(settings.cache_ttl)
        _cache_kind = "in-memory (принудительно, CACHE_BACKEND=memory)"
        logger.info("Кэш: %s", _cache_kind)
        return _cache

    try:
        import redis.asyncio as aioredis  # локальный импорт: redis может отсутствовать

        client = aioredis.from_url(settings.redis_url, decode_responses=True)
        await client.ping()
        _cache = RedisCache(client, settings.cache_ttl)
        _cache_kind = f"redis ({settings.redis_url})"
        logger.info("Кэш: Redis доступен — %s", settings.redis_url)
    except Exception as exc:  # noqa: BLE001 — важен любой сбой подключения
        _cache = InMemoryCache(settings.cache_ttl)
        _cache_kind = "in-memory (Redis недоступен)"
        logger.warning("Redis недоступен (%s). Используется in-memory кэш.", exc)
    return _cache


def get_cache() -> CacheBackend:
    """Возвращает текущий бэкенд кэша (ленивая инициализация in-memory)."""
    global _cache, _cache_kind
    if _cache is None:
        _cache = InMemoryCache(get_settings().cache_ttl)
        _cache_kind = "in-memory (ленивая инициализация)"
    return _cache


def get_cache_kind() -> str:
    """Человекочитаемое описание активного бэкенда кэша."""
    return _cache_kind


async def close_cache() -> None:
    """Корректно закрывает соединение с кэшем при остановке приложения."""
    if _cache is not None:
        await _cache.close()


def cache_key_movie(movie_id: int) -> str:
    """Ключ кэша для одного фильма."""
    return f"movie:{movie_id}"
