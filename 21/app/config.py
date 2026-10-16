"""Конфигурация приложения: все настройки читаются из переменных окружения."""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

DEFAULT_DATABASE_URL = "sqlite:///./data/hotel.db"
DEV_JWT_SECRET = "dev-secret-change-me-before-deployment"


@dataclass(frozen=True)
class Settings:
    """Настройки приложения, полученные из окружения."""

    app_name: str = "Hotel Booking API"
    app_version: str = "1.0.0"
    database_url: str = DEFAULT_DATABASE_URL
    sql_echo: bool = False
    jwt_secret: str = DEV_JWT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 60
    log_level: str = "INFO"
    admin_email: str = ""
    admin_password: str = ""
    admin_full_name: str = "Администратор отеля"


def _env_flag(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_settings() -> Settings:
    """Собрать настройки из переменных окружения."""
    return Settings(
        app_name=os.getenv("APP_NAME", "Hotel Booking API"),
        app_version=os.getenv("APP_VERSION", "1.0.0"),
        database_url=os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL),
        sql_echo=_env_flag(os.getenv("SQL_ECHO")),
        jwt_secret=os.getenv("JWT_SECRET", DEV_JWT_SECRET),
        jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
        access_token_ttl_minutes=int(os.getenv("ACCESS_TOKEN_TTL_MINUTES", "60")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        admin_email=os.getenv("ADMIN_EMAIL", ""),
        admin_password=os.getenv("ADMIN_PASSWORD", ""),
        admin_full_name=os.getenv("ADMIN_FULL_NAME", "Администратор отеля"),
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Настройки приложения по умолчанию (кэшируются на время процесса)."""
    return load_settings()
