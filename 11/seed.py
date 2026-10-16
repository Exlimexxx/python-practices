"""Первичное наполнение БД кинотеатра: схема + фильмы + залы + сеансы.

Запуск:  python seed.py [--db path]
"""
from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

from db import DB_PATH, connect
from seed_movies import MOVIES, seed_movies

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("seed")

BASE_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = BASE_DIR / "schema.sql"

#: Залы кинотеатра (id присваиваются по порядку, начиная с 1).
HALLS: tuple[tuple[str, int], ...] = (
    ("Зал 1 «IMAX»", 120),
    ("Зал 2 «Комфорт»", 80),
    ("Зал 3 «VIP»", 30),
    ("Зал 4 «Летний»", 60),
)

#: Сеансы: (movie_id, hall_id, start_time, price, tickets_sold) — 14 записей.
SCREENINGS: tuple[tuple[int, int, str, float, int], ...] = (
    (1, 1, "2025-06-01 19:30:00", 650.0, 95),
    (2, 1, "2025-06-01 22:00:00", 700.0, 60),
    (3, 2, "2025-06-02 19:00:00", 600.0, 72),
    (5, 3, "2025-06-03 18:00:00", 800.0, 25),
    (6, 3, "2025-06-03 20:30:00", 750.0, 18),
    (11, 1, "2025-06-04 19:30:00", 680.0, 110),
    (12, 2, "2025-06-05 19:15:00", 520.0, 55),
    (1, 1, "2025-06-05 22:15:00", 500.0, 30),
    (8, 4, "2025-06-06 19:00:00", 450.0, 44),
    (10, 4, "2025-06-06 13:00:00", 300.0, 52),
    (7, 3, "2025-06-07 20:00:00", 780.0, 12),
    (9, 2, "2025-06-07 18:30:00", 540.0, 66),
    (2, 4, "2025-06-08 19:45:00", 470.0, 58),
    (5, 4, "2025-06-08 19:00:00", 520.0, 35),
)


def create_schema(conn) -> None:
    """Выполняет schema.sql (DROP + CREATE + индексы)."""
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))


def seed_halls_and_screenings(conn) -> None:
    """Добавляет залы и сеансы параметризованными запросами."""
    conn.executemany("INSERT INTO halls (name, capacity) VALUES (?, ?)", HALLS)
    conn.executemany(
        "INSERT INTO screenings (movie_id, hall_id, start_time, price, tickets_sold) "
        "VALUES (?, ?, ?, ?, ?)",
        SCREENINGS,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Наполнение БД кинотеатра (вариант 4)")
    parser.add_argument("--db", default=str(DB_PATH), help="Путь к файлу SQLite")
    args = parser.parse_args()

    db_path = Path(args.db)
    if db_path.exists():
        os.remove(db_path)
        print(f"[seed] удалён старый файл БД: {db_path.name}")

    conn = connect(db_path)
    try:
        create_schema(conn)
        print("[seed] схема создана: 6 таблиц, 6 индексов, ограничения PK/FK/NOT NULL/UNIQUE/CHECK")

        movies_count, genres_count, links = seed_movies(conn)
        seed_halls_and_screenings(conn)
        conn.commit()

        print(f"[seed] фильмов: {movies_count} (требуется >= 10)")
        print(f"[seed] жанров: {genres_count}")
        print(f"[seed] связей N:M movie_genres: {links}")
        print(f"[seed] залов: {len(HALLS)}")
        print(f"[seed] сеансов: {len(SCREENINGS)}")
        print("[seed] база данных готова:", db_path)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
