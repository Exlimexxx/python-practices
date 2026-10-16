"""Конфигурация приложения (лабораторная работа №15, вариант 4 «Отель»).

Все настройки читаются из переменных окружения, чтобы не хранить их
жёстко в исходном коде (требование п. 24 методички).
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> None:
    """Минимальный загрузчик файла .env (без внешних зависимостей).

    Реальные секреты в репозиторий не попадают, поэтому .env читается,
    только если он существует локально.
    """
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value
    logger.debug("Файл .env загружен: %s", path)


def _as_bool(value: str | None, default: bool = False) -> bool:
    """Приводит строковое значение переменной окружения к bool."""
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "да"}


def _as_int(value: str | None, default: int) -> int:
    """Приводит строковое значение переменной окружения к int."""
    if value is None or not value.strip():
        return default
    try:
        return int(value)
    except ValueError:
        logger.warning("Некорректное целое %r, используется %s", value, default)
        return default


@dataclass(frozen=True)
class Settings:
    """Иммутабельный набор настроек приложения."""

    SECRET_KEY: str = "dev-secret-key-change-me"
    DATABASE_URL: str = "sqlite:///instance/hotel.db"
    FLASK_ENV: str = "development"
    DEBUG: bool = True
    TESTING: bool = False
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str | None = None
    SQL_ECHO: bool = False
    SEED_DEMO: bool = False
    HOST: str = "127.0.0.1"
    PORT: int = 5015
    BASE_DIR: Path = field(default_factory=lambda: BASE_DIR)

    @classmethod
    def from_env(cls, **overrides: object) -> "Settings":
        """Собирает настройки из окружения и точечных переопределений."""
        _load_dotenv(BASE_DIR / ".env")
        env = os.environ.get("FLASK_ENV", "development")
        raw: dict[str, object] = {
            "SECRET_KEY": os.environ.get("SECRET_KEY", "dev-secret-key-change-me"),
            "DATABASE_URL": os.environ.get("DATABASE_URL", "sqlite:///instance/hotel.db"),
            "FLASK_ENV": env,
            "DEBUG": _as_bool(os.environ.get("FLASK_DEBUG"), env == "development"),
            "TESTING": _as_bool(os.environ.get("TESTING"), False),
            "LOG_LEVEL": os.environ.get("LOG_LEVEL", "INFO"),
            "LOG_FILE": os.environ.get("LOG_FILE") or None,
            "SQL_ECHO": _as_bool(os.environ.get("SQL_ECHO"), False),
            "SEED_DEMO": _as_bool(os.environ.get("SEED_DEMO"), False),
            "HOST": os.environ.get("HOST", "127.0.0.1"),
            "PORT": _as_int(os.environ.get("PORT"), 5015),
        }
        raw.update(overrides)
        return cls(**raw)  # type: ignore[arg-type]

    def database_path(self) -> Path:
        """Возвращает абсолютный путь к файлу SQLite (для sqlite:///)."""
        if self.DATABASE_URL.startswith("sqlite:///"):
            raw_path = self.DATABASE_URL[len("sqlite:///"):]
            candidate = Path(raw_path)
            if not candidate.is_absolute():
                candidate = (self.BASE_DIR / candidate).resolve()
            return candidate
        raise ValueError("База данных не является SQLite-файлом")

    def as_flask_config(self) -> dict[str, object]:
        """Преобразует настройки в конфигурацию Flask."""
        return {
            "SECRET_KEY": self.SECRET_KEY,
            "DEBUG": self.DEBUG,
            "TESTING": self.TESTING,
            "DATABASE_URL": self.DATABASE_URL,
            "SQL_ECHO": self.SQL_ECHO,
            "SETTINGS": self,
        }
