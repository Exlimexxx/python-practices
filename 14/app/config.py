"""Конфигурация приложения.

Все настройки читаются из переменных окружения (см. .env.example).
Жёстко прописывать параметры подключения в коде нельзя (п. 41 методички).
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    """Неизменяемый набор настроек приложения."""

    app_name: str
    app_version: str
    app_env: str
    database_url: str
    redis_url: str
    cache_backend: str        # auto | memory | redis
    cache_ttl: int
    log_level: str
    default_limit: int
    max_limit: int


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Возвращает настройки, собранные из переменных окружения."""
    return Settings(
        app_name=os.getenv("APP_NAME", "Cinema Movies REST API"),
        app_version=os.getenv("APP_VERSION", "1.0.0"),
        app_env=os.getenv("APP_ENV", "development"),
        database_url=os.getenv("DATABASE_URL", "sqlite:///./movies.db"),
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        cache_backend=os.getenv("CACHE_BACKEND", "auto").lower(),
        cache_ttl=int(os.getenv("CACHE_TTL", "60")),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        default_limit=int(os.getenv("DEFAULT_LIMIT", "20")),
        max_limit=int(os.getenv("MAX_LIMIT", "100")),
    )
