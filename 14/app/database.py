"""Подключение к базе данных через SQLAlchemy ORM."""
from __future__ import annotations

import logging

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Базовый класс для всех ORM-моделей приложения."""


def build_engine(database_url: str) -> Engine:
    """Создаёт движок SQLAlchemy с учётом особенностей SQLite."""
    connect_args: dict = {}
    if database_url.startswith("sqlite"):
        # SQLite по умолчанию привязан к потоку — для FastAPI это неприемлемо.
        connect_args["check_same_thread"] = False
    return create_engine(database_url, connect_args=connect_args, future=True)


engine: Engine = build_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, class_=Session)


def _sqlite_casefold(value):
    """Регистронезависимое сравнение строк для SQLite.

    Встроенный в SQLite `lower()`/LIKE работает без учёта регистра только для
    латиницы, поэтому кириллица («Матрица» и «матрица») не совпадала.
    Регистрируем собственную UDF casefold().
    """
    return value.casefold() if isinstance(value, str) else value


@event.listens_for(engine, "connect")
def _register_sqlite_functions(dbapi_connection, connection_record) -> None:
    """Регистрирует Unicode-функцию casefold() при подключении к SQLite."""
    if engine.dialect.name == "sqlite":
        dbapi_connection.create_function("casefold", 1, _sqlite_casefold)


def init_db() -> None:
    """Создаёт таблицы, если они ещё не существуют."""
    from .models import movie  # noqa: F401  (регистрация модели в metadata)

    Base.metadata.create_all(bind=engine)
    logger.info("Схема БД инициализирована (%s)", engine.url.render_as_string(hide_password=True))


def get_db():
    """FastAPI-зависимость: выдаёт сессию БД и закрывает её после запроса."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
