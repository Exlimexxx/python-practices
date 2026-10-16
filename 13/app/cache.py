"""RedisCache — слой доступа к Redis.

Предоставляет типизированную обёртку над redis-py (или in-memory аналогом):
строки, хэши, списки, множества, сортированные множества, TTL, счётчики,
а также JSON-хелперы для кэша документов.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from .errors import SerializationError

logger = logging.getLogger(__name__)


class RedisCache:
    """Обёртка над Redis для нужд приложения «Кинотеатр — фильмы»."""

    def __init__(self, client: Any, namespace: str = "cinema") -> None:
        self.client = client
        self.namespace = namespace

    # ------------------------------------------------------------- ключи
    def key(self, *parts: Any) -> str:
        """Построить ключ с общим префиксом: cinema:movie:12."""
        return ":".join([self.namespace, *(str(p) for p in parts)])

    # ------------------------------------------------------- базовые команды
    def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """SET [EX ttl] — записать строковое значение."""
        result = self.client.set(key, value, ex=ttl) if ttl else self.client.set(key, value)
        return bool(result)

    def get(self, key: str) -> Any:
        """GET — прочитать значение."""
        return self.client.get(key)

    def delete(self, *keys: str) -> int:
        """DEL — удалить ключи."""
        if not keys:
            return 0
        return int(self.client.delete(*keys))

    def exists(self, *keys: str) -> int:
        """EXISTS — проверить наличие ключей."""
        return int(self.client.exists(*keys))

    def expire(self, key: str, ttl: int) -> bool:
        """EXPIRE — установить время жизни."""
        return bool(self.client.expire(key, ttl))

    def ttl(self, key: str) -> int:
        """TTL — узнать остаток времени жизни."""
        return int(self.client.ttl(key))

    def incr(self, key: str, amount: int = 1) -> int:
        """INCR/INCRBY — атомарный счётчик."""
        return int(self.client.incr(key, amount))

    def type(self, key: str) -> str:
        return str(self.client.type(key))

    def keys(self, pattern: str = "*") -> list[str]:
        return sorted(self.client.keys(pattern))

    def flush_namespace(self) -> int:
        """Удалить все ключи приложения (очистка кэша)."""
        keys = self.client.keys(self.namespace + ":*")
        if not keys:
            return 0
        return int(self.client.delete(*keys))

    # ------------------------------------------------------------- Hash
    def hset(self, key: str, mapping: dict[str, Any]) -> int:
        """HSET — записать хэш."""
        return int(self.client.hset(key, mapping={k: v for k, v in mapping.items()}))

    def hget(self, key: str, field: str) -> Any:
        """HGET — прочитать поле хэша."""
        return self.client.hget(key, field)

    def hgetall(self, key: str) -> dict[str, Any]:
        """HGETALL — прочитать весь хэш."""
        data = self.client.hgetall(key)
        return dict(data) if data else {}

    def hdel(self, key: str, *fields: str) -> int:
        return int(self.client.hdel(key, *fields))

    # ------------------------------------------------------------- List
    def rpush(self, key: str, *values: Any) -> int:
        """RPUSH — добавить элементы в конец списка."""
        return int(self.client.rpush(key, *values))

    def lpush(self, key: str, *values: Any) -> int:
        return int(self.client.lpush(key, *values))

    def lrange(self, key: str, start: int = 0, end: int = -1) -> list[Any]:
        """LRANGE — прочитать элементы списка."""
        return list(self.client.lrange(key, start, end))

    def ltrim(self, key: str, start: int, end: int) -> bool:
        return bool(self.client.ltrim(key, start, end))

    def llen(self, key: str) -> int:
        return int(self.client.llen(key))

    # -------------------------------------------------------------- Set
    def sadd(self, key: str, *values: Any) -> int:
        """SADD — добавить в множество."""
        return int(self.client.sadd(key, *values))

    def smembers(self, key: str) -> set[Any]:
        """SMEMBERS — все элементы множества."""
        return set(self.client.smembers(key))

    def srem(self, key: str, *values: Any) -> int:
        return int(self.client.srem(key, *values))

    def sismember(self, key: str, value: Any) -> bool:
        return bool(self.client.sismember(key, value))

    # -------------------------------------------------------- Sorted Set
    def zadd(self, key: str, mapping: dict[str, float]) -> int:
        """ZADD — добавить элементы с рейтингом."""
        return int(self.client.zadd(key, mapping))

    def zrange(self, key: str, start: int = 0, end: int = -1, withscores: bool = False):
        """ZRANGE — элементы по возрастанию рейтинга."""
        return self.client.zrange(key, start, end, withscores=withscores)

    def zrevrange(self, key: str, start: int = 0, end: int = -1, withscores: bool = False):
        """ZREVRANGE — элементы по убыванию рейтинга."""
        return self.client.zrevrange(key, start, end, withscores=withscores)

    def zscore(self, key: str, member: str) -> float | None:
        return self.client.zscore(key, member)

    def zrem(self, key: str, *members: str) -> int:
        return int(self.client.zrem(key, *members))

    # ------------------------------------------------------------ JSON
    def set_json(self, key: str, payload: Any, ttl: int | None = None) -> bool:
        """Сериализовать объект в JSON и записать в кэш."""
        try:
            raw = json.dumps(payload, ensure_ascii=False, default=str)
        except (TypeError, ValueError) as exc:
            raise SerializationError(f"Не удалось сериализовать объект в JSON: {exc}") from exc
        return self.set(key, raw, ttl=ttl)

    def get_json(self, key: str) -> Any:
        """Прочитать JSON из кэша (None при промахе)."""
        raw = self.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (TypeError, ValueError) as exc:
            logger.warning("Повреждённое значение в кэше по ключу %s: %s", key, exc)
            self.delete(key)
            return None

    def ping(self) -> bool:
        return bool(self.client.ping())
