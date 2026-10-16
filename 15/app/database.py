"""Инициализация SQLAlchemy: движок, сессии, базовый класс моделей."""
from __future__ import annotations

import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, scoped_session, sessionmaker

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Базовый декларативный класс для всех ORM-моделей."""


class Database:
    """Обёртка над движком SQLAlchemy и фабрикой сессий.

    Сессии хранятся в scoped_session, поэтому в рамках одного HTTP-запроса
    используется одна и та же сессия.
    """

    def __init__(self, url: str, *, echo: bool = False, base_dir: Path | None = None) -> None:
        self.url = url
        self._base_dir = base_dir
        self._prepare_sqlite_directory()
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        self.engine: Engine = create_engine(
            url,
            echo=echo,
            future=True,
            connect_args=connect_args,
        )
        self.session_factory = sessionmaker(
            bind=self.engine,
            autoflush=False,
            expire_on_commit=False,
            class_=Session,
        )
        self.session = scoped_session(self.session_factory)
        if url.startswith("sqlite"):
            self._register_unicode_lower()
        logger.info("Инициализирован движок БД: %s", url)

    @staticmethod
    def _register_unicode_lower() -> None:
        """Регистрирует SQL-функцию u_lower для регистронезависимого поиска.

        Встроенные LIKE/lower в SQLite работают без учёта регистра только для
        латиницы, поэтому для поиска по русскоязычным данным используется
        собственная функция, опирающаяся на str.lower() языка Python.
        """
        @event.listens_for(Engine, "connect")
        def _on_connect(dbapi_connection: object, connection_record: object) -> None:
            create_function = getattr(dbapi_connection, "create_function", None)
            if create_function is None:
                return
            create_function(
                "u_lower",
                1,
                lambda value: value.lower() if isinstance(value, str) else value,
            )

    def _prepare_sqlite_directory(self) -> None:
        """Создаёт каталог для файла SQLite, если он отсутствует."""
        if not self.url.startswith("sqlite:///"):
            return
        raw_path = self.url[len("sqlite:///"):]
        if raw_path == ":memory:":
            return
        path = Path(raw_path)
        if not path.is_absolute() and self._base_dir is not None:
            path = (self._base_dir / path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)

    def create_all(self) -> None:
        """Создаёт все таблицы по метаданным моделей."""
        Base.metadata.create_all(self.engine)
        logger.info("Таблицы созданы: %s", ", ".join(sorted(Base.metadata.tables)))

    def drop_all(self) -> None:
        """Удаляет все таблицы (используется в тестах)."""
        Base.metadata.drop_all(self.engine)

    def get_session(self) -> Session:
        """Возвращает текущую сессию."""
        return self.session()

    def remove_session(self) -> None:
        """Закрывает сессию текущего контекста."""
        self.session.remove()

    @contextmanager
    def session_scope(self) -> Iterator[Session]:
        """Контекстный менеджер для ручной работы с сессией."""
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            self.session.remove()

    def dispose(self) -> None:
        """Освобождает ресурсы движка."""
        self.session.remove()
        self.engine.dispose()
