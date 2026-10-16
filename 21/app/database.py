"""Подключение к базе данных и фабрика сессий."""
from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker

from app.models.base import Base

SQLITE_PREFIX = "sqlite"


def _prepare_sqlite_directory(database_url: str) -> None:
    url = make_url(database_url)
    if url.get_backend_name() != SQLITE_PREFIX or not url.database:
        return
    if url.database in {":memory:", ""}:
        return
    Path(url.database).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)


def create_engine_from_url(database_url: str, *, echo: bool = False) -> Engine:
    """Создать движок SQLAlchemy; для SQLite разрешено использование в потоках."""
    _prepare_sqlite_directory(database_url)
    connect_args = (
        {"check_same_thread": False} if database_url.startswith(SQLITE_PREFIX) else {}
    )
    return create_engine(
        database_url,
        echo=echo,
        future=True,
        pool_pre_ping=True,
        connect_args=connect_args,
    )


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(
        bind=engine, autoflush=False, expire_on_commit=False, class_=Session
    )


def init_database(engine: Engine) -> None:
    """Создать таблицы, если они ещё не существуют."""
    Base.metadata.create_all(engine)


def drop_database(engine: Engine) -> None:
    Base.metadata.drop_all(engine)
