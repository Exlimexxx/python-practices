"""Кэш-слой приложения.

Если сервер Redis доступен — используется настоящий Redis (класс RedisCache).
Если Redis недоступен (как в этой среде) — включается InMemoryCache,
встроенная реализация, которая эмулирует команды Redis:
SET, GET, DELETE, EXPIRE, INCR, TTL и поведение ключей по времени жизни.
Интерфейс у обоих классов одинаковый (см. протокол CacheBackend).
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Protocol, runtime_checkable

logger = logging.getLogger("cinema.cache")


@runtime_checkable
class CacheBackend(Protocol):
    """Общий интерфейс кэша (Redis или in-memory эмуляция)."""

    name: str

    def set(self, key: str, value: str, ttl: int | None = None) -> None: ...
    def get(self, key: str) -> str | None: ...
    def delete(self, key: str) -> bool: ...
    def expire(self, key: str, ttl: int) -> bool: ...
    def incr(self, key: str, amount: int = 1) -> int: ...
    def ttl(self, key: str) -> int: ...
    def flush(self) -> None: ...


class InMemoryCache:
    """Эмуляция Redis в памяти процесса.

    Хранит строковые значения и абсолютное время истечения ключа,
    поэтому поддерживает те же операции, что и настоящий Redis.
    """

    name = "in-memory (эмуляция Redis)"

    def __init__(self) -> None:
        self._values: dict[str, str] = {}
        self._expires: dict[str, float] = {}
        self._lock = threading.Lock()

    # --- внутренние помощники -----------------------------------------
    def _purge_if_expired(self, key: str) -> None:
        deadline = self._expires.get(key)
        if deadline is not None and deadline <= time.monotonic():
            self._values.pop(key, None)
            self._expires.pop(key, None)

    def _exists(self, key: str) -> bool:
        self._purge_if_expired(key)
        return key in self._values

    # --- операции Redis ------------------------------------------------
    def set(self, key: str, value: str, ttl: int | None = None) -> None:
        """SET key value [EX ttl]."""
        with self._lock:
            self._values[key] = value
            if ttl is None:
                self._expires.pop(key, None)
            else:
                self._expires[key] = time.monotonic() + ttl

    def get(self, key: str) -> str | None:
        """GET key."""
        with self._lock:
            self._purge_if_expired(key)
            return self._values.get(key)

    def delete(self, key: str) -> bool:
        """DEL key -> True, если ключ существовал."""
        with self._lock:
            existed = self._exists(key)
            self._values.pop(key, None)
            self._expires.pop(key, None)
            return existed

    def expire(self, key: str, ttl: int) -> bool:
        """EXPIRE key ttl -> True, если TTL установлен."""
        with self._lock:
            if not self._exists(key):
                return False
            self._expires[key] = time.monotonic() + ttl
            return True

    def incr(self, key: str, amount: int = 1) -> int:
        """INCRBY key amount (счётчики попаданий/промахов)."""
        with self._lock:
            self._purge_if_expired(key)
            current = int(self._values.get(key, "0")) if key in self._values else 0
            current += amount
            self._values[key] = str(current)
            return current

    def ttl(self, key: str) -> int:
        """TTL key: -2 — нет ключа, -1 — без срока, иначе секунды."""
        with self._lock:
            self._purge_if_expired(key)
            if key not in self._values:
                return -2
            deadline = self._expires.get(key)
            if deadline is None:
                return -1
            return max(0, int(round(deadline - time.monotonic())))

    def flush(self) -> None:
        with self._lock:
            self._values.clear()
            self._expires.clear()


class RedisCache:
    """Тонкая обёртка над клиентом redis-py (decode_responses=True)."""

    name = "redis"

    def __init__(self, client) -> None:
        self._client = client

    def set(self, key: str, value: str, ttl: int | None = None) -> None:
        if ttl is None:
            self._client.set(key, value)
        else:
            self._client.set(key, value, ex=ttl)

    def get(self, key: str) -> str | None:
        return self._client.get(key)

    def delete(self, key: str) -> bool:
        return bool(self._client.delete(key))

    def expire(self, key: str, ttl: int) -> bool:
        return bool(self._client.expire(key, ttl))

    def incr(self, key: str, amount: int = 1) -> int:
        return int(self._client.incrby(key, amount))

    def ttl(self, key: str) -> int:
        return int(self._client.ttl(key))

    def flush(self) -> None:
        self._client.flushdb()


def create_cache(host: str = "127.0.0.1", port: int = 6379,
                 socket_timeout: float = 0.4) -> CacheBackend:
    """Возвращает RedisCache, если сервер Redis отвечает, иначе InMemoryCache."""
    try:
        import redis  # type: ignore

        client = redis.Redis(host=host, port=port, socket_connect_timeout=socket_timeout,
                             socket_timeout=socket_timeout, decode_responses=True)
        client.ping()
        logger.info("Redis доступен по адресу %s:%s — используется реальный сервер", host, port)
        return RedisCache(client)
    except Exception as exc:  # pragma: no cover - зависит от среды
        logger.warning("Redis недоступен (%s: %s) — включаю in-memory эмуляцию",
                       type(exc).__name__, exc)
        return InMemoryCache()
