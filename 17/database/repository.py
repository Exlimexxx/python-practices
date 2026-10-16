"""SQLite-хранилище кинотеатра для Telegram-бота (вариант 4)."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

SEED_MOVIES = [
    ("Космическое путешествие", "Фантастика", 121, 8.2),
    ("Последний детектив", "Детектив", 108, 7.6),
    ("Летний маршрут", "Драма", 114, 7.1),
    ("Смешной переполох", "Комедия", 96, 6.9),
    ("Город героев", "Приключения", 132, 8.0),
    ("Тайна старого маяка", "Детектив", 101, 7.4),
    ("За горизонтом", "Фантастика", 128, 8.4),
    ("Однажды в октябре", "Драма", 110, 7.8),
    ("Каникулы наоборот", "Комедия", 93, 6.8),
    ("Легенда северного леса", "Приключения", 119, 7.9),
    ("Планета океан", "Документальный", 88, 8.1),
    ("Музыка улиц", "Музыкальный", 105, 7.3),
]


class CinemaRepository:
    """Репозиторий SQLite. Каждый экземпляр хранит собственное соединение."""

    def __init__(self, db_path: str | Path = "cinema.db", seed: bool = True) -> None:
        self.db_path = str(db_path)
        self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self._create_schema()
        if seed:
            self._seed_if_empty()

    def _create_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS genres (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            );
            CREATE TABLE IF NOT EXISTS movies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL UNIQUE,
                genre_id INTEGER NOT NULL REFERENCES genres(id),
                duration INTEGER NOT NULL CHECK(duration BETWEEN 1 AND 400),
                rating REAL NOT NULL CHECK(rating BETWEEN 0 AND 10)
            );
            CREATE TABLE IF NOT EXISTS halls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                rows_count INTEGER NOT NULL CHECK(rows_count > 0),
                seats_per_row INTEGER NOT NULL CHECK(seats_per_row > 0)
            );
            CREATE TABLE IF NOT EXISTS screenings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                movie_id INTEGER NOT NULL REFERENCES movies(id),
                hall_id INTEGER NOT NULL REFERENCES halls(id),
                starts_at TEXT NOT NULL,
                price REAL NOT NULL CHECK(price >= 0)
            );
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                screening_id INTEGER NOT NULL REFERENCES screenings(id),
                row_no INTEGER NOT NULL,
                seat_no INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'booked',
                UNIQUE(screening_id, row_no, seat_no)
            );
            """
        )
        self.connection.commit()

    def _seed_if_empty(self) -> None:
        count = self.connection.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
        if count:
            return
        genres = sorted({item[1] for item in SEED_MOVIES})
        self.connection.executemany("INSERT INTO genres(name) VALUES (?)", [(g,) for g in genres])
        genre_ids = {r["name"]: r["id"] for r in self.connection.execute("SELECT id, name FROM genres")}
        self.connection.executemany(
            "INSERT INTO movies(title, genre_id, duration, rating) VALUES (?, ?, ?, ?)",
            [(title, genre_ids[genre], duration, rating) for title, genre, duration, rating in SEED_MOVIES],
        )
        self.connection.executemany(
            "INSERT INTO halls(name, rows_count, seats_per_row) VALUES (?, ?, ?)",
            [("Зал 1", 10, 12), ("Зал 2", 8, 10), ("Зал VIP", 4, 8)],
        )
        self.connection.executemany(
            "INSERT INTO screenings(movie_id, hall_id, starts_at, price) VALUES (?, ?, ?, ?)",
            [(i, (i % 3) + 1, f"2026-10-{20 + (i % 8):02d} {16 + (i % 5):02d}:00", 350 + 25 * (i % 4)) for i in range(1, 9)],
        )
        self.connection.execute(
            "INSERT INTO tickets(screening_id, row_no, seat_no, user_id) VALUES (1, 1, 1, 10001)"
        )
        self.connection.commit()

    def _movie_dict(self, row: sqlite3.Row | None) -> dict[str, Any] | None:
        return dict(row) if row else None

    def list_movies(self) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT m.id, m.title, g.name AS genre, m.duration, m.rating "
            "FROM movies m JOIN genres g ON g.id=m.genre_id ORDER BY m.title"
        ).fetchall()
        return [dict(row) for row in rows]

    def get_movie(self, movie_id: int) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT m.id, m.title, g.name AS genre, m.duration, m.rating "
            "FROM movies m JOIN genres g ON g.id=m.genre_id WHERE m.id=?", (movie_id,)
        ).fetchone()
        return self._movie_dict(row)

    def search_movies(self, query: str = "", genre: str = "") -> list[dict[str, Any]]:
        # SQLite lower() по умолчанию не обрабатывает кириллицу; нормализуем строки в Python.
        rows = self.connection.execute(
            "SELECT m.id, m.title, g.name AS genre, m.duration, m.rating "
            "FROM movies m JOIN genres g ON g.id=m.genre_id"
        ).fetchall()
        query_key, genre_key = query.strip().casefold(), genre.strip().casefold()
        result = [dict(row) for row in rows
                  if query_key in row["title"].casefold()
                  and (not genre_key or genre_key == row["genre"].casefold())]
        return sorted(result, key=lambda item: (-item["rating"], item["title"].casefold()))

    def add_movie(self, title: str, genre: str, duration: int, rating: float) -> int:
        title = title.strip()
        genre = genre.strip()
        if not title:
            raise ValueError("Название фильма не может быть пустым")
        if not genre:
            raise ValueError("Жанр не может быть пустым")
        if not 1 <= int(duration) <= 400:
            raise ValueError("Длительность должна быть от 1 до 400 минут")
        if not 0 <= float(rating) <= 10:
            raise ValueError("Рейтинг должен находиться в диапазоне 0..10")
        try:
            self.connection.execute("INSERT OR IGNORE INTO genres(name) VALUES (?)", (genre,))
            genre_id = self.connection.execute("SELECT id FROM genres WHERE name=?", (genre,)).fetchone()[0]
            cursor = self.connection.execute(
                "INSERT INTO movies(title, genre_id, duration, rating) VALUES (?, ?, ?, ?)",
                (title, genre_id, int(duration), float(rating)),
            )
            self.connection.commit()
            return int(cursor.lastrowid)
        except sqlite3.IntegrityError as exc:
            self.connection.rollback()
            raise ValueError("Фильм с таким названием уже существует") from exc

    def update_movie(self, movie_id: int, title: str, genre: str, duration: int, rating: float) -> bool:
        if self.get_movie(movie_id) is None:
            return False
        title = title.strip()
        genre = genre.strip()
        if not title or not genre or not 1 <= int(duration) <= 400 or not 0 <= float(rating) <= 10:
            raise ValueError("Некорректные данные фильма")
        self.connection.execute("INSERT OR IGNORE INTO genres(name) VALUES (?)", (genre,))
        genre_id = self.connection.execute("SELECT id FROM genres WHERE name=?", (genre,)).fetchone()[0]
        try:
            self.connection.execute(
                "UPDATE movies SET title=?, genre_id=?, duration=?, rating=? WHERE id=?",
                (title, genre_id, int(duration), float(rating), movie_id),
            )
            self.connection.commit()
            return True
        except sqlite3.IntegrityError as exc:
            self.connection.rollback()
            raise ValueError("Фильм с таким названием уже существует") from exc

    def delete_movie(self, movie_id: int) -> bool:
        if self.get_movie(movie_id) is None:
            return False
        used = self.connection.execute("SELECT 1 FROM screenings WHERE movie_id=? LIMIT 1", (movie_id,)).fetchone()
        if used:
            raise ValueError("Нельзя удалить фильм, у которого есть сеансы")
        self.connection.execute("DELETE FROM movies WHERE id=?", (movie_id,))
        self.connection.commit()
        return True

    def list_screenings(self) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT s.id, m.title, h.name AS hall, s.starts_at, s.price, h.rows_count, h.seats_per_row "
            "FROM screenings s JOIN movies m ON m.id=s.movie_id JOIN halls h ON h.id=s.hall_id "
            "ORDER BY s.starts_at"
        ).fetchall()
        return [dict(row) for row in rows]

    def get_screening(self, screening_id: int) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT s.id, s.movie_id, s.hall_id, m.title, h.name AS hall, s.starts_at, s.price, h.rows_count, h.seats_per_row "
            "FROM screenings s JOIN movies m ON m.id=s.movie_id JOIN halls h ON h.id=s.hall_id WHERE s.id=?",
            (screening_id,),
        ).fetchone()
        return self._movie_dict(row)

    def book_ticket(self, screening_id: int, row_no: int, seat_no: int, user_id: int) -> int:
        screening = self.get_screening(screening_id)
        if screening is None:
            raise ValueError("Сеанс не найден")
        if not 1 <= int(row_no) <= screening["rows_count"]:
            raise ValueError("Такого ряда в зале нет")
        if not 1 <= int(seat_no) <= screening["seats_per_row"]:
            raise ValueError("Такого места в ряду нет")
        try:
            cursor = self.connection.execute(
                "INSERT INTO tickets(screening_id, row_no, seat_no, user_id) VALUES (?, ?, ?, ?)",
                (screening_id, row_no, seat_no, user_id),
            )
            self.connection.commit()
            return int(cursor.lastrowid)
        except sqlite3.IntegrityError as exc:
            self.connection.rollback()
            raise ValueError("Это место уже забронировано") from exc

    def cancel_ticket(self, ticket_id: int, user_id: int) -> bool:
        cursor = self.connection.execute(
            "DELETE FROM tickets WHERE id=? AND user_id=?", (ticket_id, user_id)
        )
        self.connection.commit()
        return cursor.rowcount == 1

    def close(self) -> None:
        self.connection.close()
