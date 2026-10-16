"""Настройка подключения к базе данных и фабрика сессий (SQLAlchemy 2.x).

Строка подключения настраивается через переменную окружения HOTEL_DATABASE_URL.
По умолчанию используется SQLite (сервер PostgreSQL в учебной среде не установлен),
но приложение готово к переключению на PostgreSQL, например:

    postgresql+psycopg://hotel_user:secret@localhost:5432/hotel_db
"""
from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

#: Имя переменной окружения, переопределяющей строку подключения.
DATABASE_URL_ENV = "HOTEL_DATABASE_URL"

#: Строка подключения по умолчанию (файл SQLite рядом с запускаемым скриптом).
DEFAULT_DATABASE_URL = "sqlite:///hotel.db"

#: Пример строки подключения для PostgreSQL (используется при наличии сервера).
POSTGRESQL_EXAMPLE_URL = "postgresql+psycopg://hotel_user:secret@localhost:5432/hotel_db"


def get_database_url() -> str:
    """Вернуть строку подключения: из переменной окружения либо значение по умолчанию."""
    return os.getenv(DATABASE_URL_ENV, DEFAULT_DATABASE_URL)


class Base(DeclarativeBase):
    """Декларативная база SQLAlchemy 2.x для всех ORM-моделей."""


_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def configure_database(url: str | None = None, *, echo: bool = False) -> Engine:
    """Создать (пере)подключение к БД и фабрику сессий.

    :param url: строка подключения; если None — берётся get_database_url().
    :param echo: выводить ли SQL-запросы в лог (полезно при отладке).
    :return: созданный Engine.
    """
    global _engine, _session_factory
    resolved = url or get_database_url()
    kwargs: dict[str, object] = {"echo": echo, "future": True}
    if resolved.startswith("sqlite") and ":memory:" in resolved:
        # Одно общее соединение, иначе каждая сессия увидит свою пустую БД.
        kwargs["poolclass"] = StaticPool
        kwargs["connect_args"] = {"check_same_thread": False}
    _engine = create_engine(resolved, **kwargs)
    if _engine.dialect.name == "sqlite":
        # SQLite по умолчанию не проверяет внешние ключи — включаем вручную.
        event.listen(_engine, "connect", _enable_sqlite_foreign_keys)
    _session_factory = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False)
    return _engine


def _enable_sqlite_foreign_keys(dbapi_connection: object, _record: object) -> None:
    """Включить контроль внешних ключей для каждого соединения SQLite."""
    cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def get_engine() -> Engine:
    """Получить Engine, создав его при первом обращении."""
    if _engine is None:
        configure_database()
    assert _engine is not None
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    """Получить фабрику сессий, создав её при первом обращении."""
    if _session_factory is None:
        configure_database()
    assert _session_factory is not None
    return _session_factory


def init_db() -> None:
    """Создать все таблицы, описанные в моделях (create_all)."""
    from app import models  # noqa: F401  (импорт регистрирует таблицы в metadata)

    Base.metadata.create_all(get_engine())


def drop_db() -> None:
    """Удалить все таблицы (используется в тестах и демонстрациях)."""
    from app import models  # noqa: F401

    Base.metadata.drop_all(get_engine())


@contextmanager
def session_scope() -> Iterator[Session]:
    """Контекстный менеджер сессии: commit при успехе, rollback при ошибке."""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
