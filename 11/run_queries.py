"""Выполняет все запросы из queries.sql и печатает результаты.

Запуск:  python run_queries.py [--db cinema.db] [--sql queries.sql]
"""
from __future__ import annotations

import argparse
import re
import sqlite3
from pathlib import Path

from db import DB_PATH, connect

BASE_DIR = Path(__file__).resolve().parent
QUERY_RE = re.compile(r"^-- @query\s+(.*)$", re.MULTILINE)


def load_queries(path: Path) -> list[tuple[str, str]]:
    """Разбирает queries.sql на пары (название запроса, SQL)."""
    text = path.read_text(encoding="utf-8")
    parts = QUERY_RE.split(text)
    chunks = parts[1:]
    result: list[tuple[str, str]] = []
    for i in range(0, len(chunks), 2):
        name = re.sub(r"^\d+\.\s*", "", chunks[i].strip())
        sql = chunks[i + 1].strip().rstrip(";").strip()
        if sql:
            result.append((name, sql))
    return result


def format_value(value: object) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def print_rows(cursor: sqlite3.Cursor, rows: list[sqlite3.Row]) -> None:
    if not rows:
        print("  (нет строк)")
        return
    columns = [d[0] for d in cursor.description or []]
    print("  " + " | ".join(columns))
    print("  " + "-" * (len(" | ".join(columns))))
    for row in rows:
        print("  " + " | ".join(format_value(row[col]) for col in columns))


def main() -> int:
    parser = argparse.ArgumentParser(description="Запуск SQL-запросов из queries.sql")
    parser.add_argument("--db", default=str(DB_PATH))
    parser.add_argument("--sql", default=str(BASE_DIR / "queries.sql"))
    args = parser.parse_args()

    queries = load_queries(Path(args.sql))
    conn = connect(args.db)
    print("=" * 78)
    print(f"ВЫПОЛНЕНИЕ ЗАПРОСОВ: {Path(args.sql).name}  (БД: {Path(args.db).name})")
    print(f"Всего запросов: {len(queries)}")
    print("=" * 78)

    total_rows = 0
    try:
        for index, (name, sql) in enumerate(queries, start=1):
            print()
            print(f"--- Запрос {index}. {name} ---")
            print("SQL:", " ".join(sql.split()))
            cursor = conn.execute(sql)
            if cursor.description is None:
                conn.commit()
                print(f"  Затронуто строк: {cursor.rowcount}")
            else:
                rows = cursor.fetchall()
                total_rows += len(rows)
                print(f"  Получено строк: {len(rows)}")
                print_rows(cursor, rows)
    finally:
        conn.close()

    print()
    print("=" * 78)
    print(f"ИТОГО: выполнено {len(queries)} запросов, прочитано {total_rows} строк.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
