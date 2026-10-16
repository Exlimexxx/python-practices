"""Низкоуровневая работа с SQLite: подключение, транзакции, хелперы.

Все запросы в проекте выполняются ТОЛЬКО с параметрами-заглушками «?»,
значения передаются отдельным кортежем. Это исключает SQL-инъекции.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Sequence

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "cinema.db"
SCHEMA_PATH = BASE_DIR / "schema.sql"


def connect(db_path: str | Path = DB_PATH) -> sqlite3.Connection:
    """Открывает соединение с включёнными внешними ключами.

    isolation_level=None переводит драйвер в режим авто-коммита:
    транзакции открываются/закрываются явными BEGIN / COMMIT / ROLLBACK.
    """
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.isolation_level = None
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Транзакция с COMMIT при успехе и ROLLBACK при любой ошибке."""
    conn.execute("BEGIN")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def fetch_all(conn: sqlite3.Connection, sql: str, params: Sequence[object] = ()) -> list[sqlite3.Row]:
    """SELECT -> список строк (параметризованный запрос)."""
    return list(conn.execute(sql, tuple(params)))


def fetch_one(conn: sqlite3.Connection, sql: str, params: Sequence[object] = ()) -> sqlite3.Row | None:
    """SELECT -> первая строка или None."""
    return conn.execute(sql, tuple(params)).fetchone()
