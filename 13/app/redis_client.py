"""Подключение к Redis и встроенный in-memory аналог.

Если сервер Redis недоступен, используется InMemoryRedis — учебная реализация
основных команд: SET/GET/DEL, EXPIRE/TTL/PERSIST, INCR/DECR, HSET/HGET/HGETALL/HDEL,
RPUSH/LPUSH/LRANGE/LLEN, SADD/SMEMBERS/SREM/SISMEMBER, ZADD/ZRANGE/ZREVRANGE/
ZSCORE/ZREM, KEYS/FLUSHDB. Поддерживаются структуры String, List, Set, Hash,
Sorted Set и TTL (секунды и миллисекунды).
"""
from __future__ import annotations

import fnmatch
import threading
import time
from typing import Any

# ---------------------------------------------------------------------------
# In-memory реализация
# ---------------------------------------------------------------------------
class InMemoryRedis:
    """Мини-эмуляция Redis с поддержкой TTL и основных типов данных."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self._expiry: dict[str, float] = {}
        self._lock = threading.RLock()

    # --------------------------------------------------------- срок жизни
    def _is_expired(self, name: str) -> bool:
        expiry = self._expiry.get(name)
        if expiry is not None and expiry <= time.time():
            self._data.pop(name, None)
            self._expiry.pop(name, None)
            return True
        return False

    def _get_entry(self, name: str) -> Any:
        self._is_expired(name)
        return self._data.get(name)

    def _set_entry(self, name: str, value: Any) -> None:
        self._data[name] = value

    def _has(self, name: str) -> bool:
        return self._get_entry(name) is not None

    # ------------------------------------------------------------- служебные
    def ping(self) -> bool:
        return True

    def keys(self, pattern: str = "*") -> list[str]:
        with self._lock:
            for name in list(self._data):
                self._is_expired(name)
            return [name for name in self._data if fnmatch.fnmatch(name, pattern)]

    def dbsize(self) -> int:
        return len(self.keys())

    def flushdb(self) -> bool:
        with self._lock:
            self._data.clear()
            self._expiry.clear()
        return True

    def type(self, name: str) -> str:
        value = self._get_entry(name)
        if value is None:
            return "none"
        if isinstance(value, dict):
            return "hash"
        if isinstance(value, list):
            return "list"
        if isinstance(value, set):
            return "set"
        if isinstance(value, _ZSet):
            return "zset"
        return "string"

    # ------------------------------------------------------------- String
    def set(
        self,
        name: str,
        value: Any,
        ex: int | None = None,
        px: int | None = None,
        nx: bool = False,
        xx: bool = False,
    ) -> bool:
        with self._lock:
            if nx and self._has(name):
                return False
            if xx and not self._has(name):
                return False
            self._set_entry(name, value)
            self._expiry.pop(name, None)
            if ex is not None:
                self._expiry[name] = time.time() + int(ex)
            elif px is not None:
                self._expiry[name] = time.time() + int(px) / 1000.0
            return True

    def get(self, name: str) -> Any:
        return self._get_entry(name)

    def delete(self, *names: str) -> int:
        removed = 0
        with self._lock:
            for name in names:
                if self._has(name):
                    self._data.pop(name, None)
                    self._expiry.pop(name, None)
                    removed += 1
        return removed

    def exists(self, *names: str) -> int:
        return sum(1 for name in names if self._has(name))

    def incr(self, name: str, amount: int = 1) -> int:
        with self._lock:
            current = self._get_entry(name)
            value = (int(current) if current is not None else 0) + int(amount)
            self._set_entry(name, value)
            return value

    def decr(self, name: str, amount: int = 1) -> int:
        return self.incr(name, -int(amount))

    # -------------------------------------------------------------- TTL
    def expire(self, name: str, time_seconds: int) -> bool:
        with self._lock:
            if not self._has(name):
                return False
            self._expiry[name] = time.time() + int(time_seconds)
            return True

    def pexpire(self, name: str, milliseconds: int) -> bool:
        with self._lock:
            if not self._has(name):
                return False
            self._expiry[name] = time.time() + int(milliseconds) / 1000.0
            return True

    def ttl(self, name: str) -> int:
        with self._lock:
            if not self._has(name):
                return -2
            expiry = self._expiry.get(name)
            if expiry is None:
                return -1
            return max(0, int(round(expiry - time.time())))

    def persist(self, name: str) -> bool:
        with self._lock:
            if name in self._expiry:
                self._expiry.pop(name)
                return True
            return False

    # -------------------------------------------------------------- Hash
    def hset(
        self,
        name: str,
        key: str | None = None,
        value: Any = None,
        mapping: dict[str, Any] | None = None,
    ) -> int:
        with self._lock:
            store = self._get_entry(name)
            if not isinstance(store, dict):
                store = {}
                self._set_entry(name, store)
            added = 0
            pairs: dict[str, Any] = {}
            if key is not None:
                pairs[str(key)] = value
            if mapping:
                pairs.update({str(k): v for k, v in mapping.items()})
            for field_name, field_value in pairs.items():
                if field_name not in store:
                    added += 1
                store[field_name] = field_value
            return added

    def hget(self, name: str, key: str) -> Any:
        store = self._get_entry(name)
        if isinstance(store, dict):
            return store.get(str(key))
        return None

    def hgetall(self, name: str) -> dict[str, Any]:
        store = self._get_entry(name)
        return dict(store) if isinstance(store, dict) else {}

    def hdel(self, name: str, *keys: str) -> int:
        store = self._get_entry(name)
        if not isinstance(store, dict):
            return 0
        removed = 0
        for key in keys:
            if str(key) in store:
                store.pop(str(key))
                removed += 1
        return removed

    def hkeys(self, name: str) -> list[str]:
        store = self._get_entry(name)
        return list(store.keys()) if isinstance(store, dict) else []

    def hexists(self, name: str, key: str) -> bool:
        return self.hget(name, key) is not None

    def hincrby(self, name: str, key: str, amount: int = 1) -> int:
        current = self.hget(name, key)
        value = (int(current) if current is not None else 0) + int(amount)
        self.hset(name, key, value)
        return value

    # -------------------------------------------------------------- List
    def rpush(self, name: str, *values: Any) -> int:
        with self._lock:
            store = self._get_entry(name)
            if not isinstance(store, list):
                store = []
                self._set_entry(name, store)
            store.extend(values)
            return len(store)

    def lpush(self, name: str, *values: Any) -> int:
        with self._lock:
            store = self._get_entry(name)
            if not isinstance(store, list):
                store = []
                self._set_entry(name, store)
            for value in values:
                store.insert(0, value)
            return len(store)

    def lrange(self, name: str, start: int, end: int) -> list[Any]:
        store = self._get_entry(name)
        if not isinstance(store, list):
            return []
        length = len(store)
        if start < 0:
            start = max(0, length + start)
        if end < 0:
            end = length + end
        return list(store[start : end + 1])

    def llen(self, name: str) -> int:
        store = self._get_entry(name)
        return len(store) if isinstance(store, list) else 0

    def ltrim(self, name: str, start: int, end: int) -> bool:
        with self._lock:
            store = self._get_entry(name)
            if not isinstance(store, list):
                return False
            length = len(store)
            if start < 0:
                start = max(0, length + start)
            if end < 0:
                end = length + end
            self._set_entry(name, store[start : end + 1])
            return True

    # --------------------------------------------------------------- Set
    def sadd(self, name: str, *values: Any) -> int:
        with self._lock:
            store = self._get_entry(name)
            if not isinstance(store, set):
                store = set()
                self._set_entry(name, store)
            added = 0
            for value in values:
                if value not in store:
                    store.add(value)
                    added += 1
            return added

    def smembers(self, name: str) -> set[Any]:
        store = self._get_entry(name)
        return set(store) if isinstance(store, set) else set()

    def srem(self, name: str, *values: Any) -> int:
        store = self._get_entry(name)
        if not isinstance(store, set):
            return 0
        removed = 0
        for value in values:
            if value in store:
                store.discard(value)
                removed += 1
        return removed

    def sismember(self, name: str, value: Any) -> bool:
        store = self._get_entry(name)
        return isinstance(store, set) and value in store

    def scard(self, name: str) -> int:
        store = self._get_entry(name)
        return len(store) if isinstance(store, set) else 0

    # --------------------------------------------------------- Sorted Set
    def zadd(self, name: str, mapping: dict[str, float], nx: bool = False) -> int:
        with self._lock:
            store = self._get_entry(name)
            if not isinstance(store, _ZSet):
                store = _ZSet()
                self._set_entry(name, store)
            added = 0
            for member, score in mapping.items():
                member_key = str(member)
                if nx and member_key in store.scores:
                    continue
                if member_key not in store.scores:
                    added += 1
                store.scores[member_key] = float(score)
            return added

    def zrange(self, name: str, start: int, end: int, withscores: bool = False, desc: bool = False):
        store = self._get_entry(name)
        if not isinstance(store, _ZSet):
            return []
        ordered = sorted(store.scores.items(), key=lambda item: (item[1], item[0]), reverse=desc)
        length = len(ordered)
        if start < 0:
            start = max(0, length + start)
        if end < 0:
            end = length + end
        chunk = ordered[start : end + 1]
        if withscores:
            return [(member, score) for member, score in chunk]
        return [member for member, _ in chunk]

    def zrevrange(self, name: str, start: int, end: int, withscores: bool = False):
        return self.zrange(name, start, end, withscores=withscores, desc=True)

    def zscore(self, name: str, member: str) -> float | None:
        store = self._get_entry(name)
        if isinstance(store, _ZSet):
            return store.scores.get(str(member))
        return None

    def zrem(self, name: str, *members: str) -> int:
        store = self._get_entry(name)
        if not isinstance(store, _ZSet):
            return 0
        removed = 0
        for member in members:
            if str(member) in store.scores:
                store.scores.pop(str(member))
                removed += 1
        return removed

    def zcard(self, name: str) -> int:
        store = self._get_entry(name)
        return len(store.scores) if isinstance(store, _ZSet) else 0

    def zrevrank(self, name: str, member: str) -> int | None:
        ordered = self.zrange(name, 0, -1, desc=True)
        try:
            return ordered.index(str(member))
        except ValueError:
            return None


class _ZSet:
    """Внутреннее представление Sorted Set."""

    def __init__(self) -> None:
        self.scores: dict[str, float] = {}

    def __repr__(self) -> str:  # pragma: no cover - отладочное представление
        return f"_ZSet({self.scores!r})"


# ---------------------------------------------------------------------------
# Подключение к настоящему Redis
# ---------------------------------------------------------------------------
def connect_redis(
    url: str = "redis://127.0.0.1:6379/0",
    socket_timeout: float = 0.8,
    allow_fallback: bool = True,
) -> tuple[Any, str, str | None]:
    """Подключиться к Redis, при недоступности вернуть in-memory реализацию."""
    error: str | None = None
    try:
        import redis as redis_module  # импорт внутри функции

        client = redis_module.Redis.from_url(
            url,
            decode_responses=True,
            socket_connect_timeout=socket_timeout,
            socket_timeout=socket_timeout,
        )
        client.ping()  # реальная проверка соединения
        return client, "redis", None
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        if not allow_fallback:
            from .errors import StorageUnavailableError

            raise StorageUnavailableError(f"Redis недоступен ({error})") from exc
    return InMemoryRedis(), "memory", error
