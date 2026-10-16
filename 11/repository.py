"""Репозитории предметной области «Кинотеатр».

Правило проекта: НИ ОДНОГО запроса со склейкой строк — все значения
передаются через заполнители «?» (параметризованные запросы).
Это защищает от SQL-инъекций.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass


class RepositoryError(RuntimeError):
    """Базовая ошибка слоя доступа к данным."""


class EntityNotFoundError(RepositoryError):
    """Запрошенная сущность не найдена в БД."""


@dataclass(frozen=True)
class Movie:
    """Фильм — основная сущность предметной области (таблица movies)."""

    id: int
    title: str
    duration: int
    rating: float
    poster_path: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Movie":
        return cls(row["id"], row["title"], row["duration"], row["rating"], row["poster_path"])


@dataclass(frozen=True)
class Hall:
    id: int
    name: str
    capacity: int

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Hall":
        return cls(row["id"], row["name"], row["capacity"])


@dataclass(frozen=True)
class Screening:
    id: int
    movie_id: int
    hall_id: int
    start_time: str
    price: float
    tickets_sold: int

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Screening":
        return cls(row["id"], row["movie_id"], row["hall_id"],
                   row["start_time"], row["price"], row["tickets_sold"])


@dataclass(frozen=True)
class Genre:
    id: int
    name: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Genre":
        return cls(row["id"], row["name"])


class MovieRepository:
    """Доступ к таблице movies и к связке movies<->genres."""

    _SELECT = "SELECT id, title, duration, rating, poster_path FROM movies"

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def all(self) -> list[Movie]:
        rows = self._conn.execute(f"{self._SELECT} ORDER BY title").fetchall()
        return [Movie.from_row(row) for row in rows]

    def get(self, movie_id: int) -> Movie:
        row = self._conn.execute(f"{self._SELECT} WHERE id = ?", (movie_id,)).fetchone()
        if row is None:
            raise EntityNotFoundError(f"Фильм id={movie_id} не найден")
        return Movie.from_row(row)

    def search(self, fragment: str) -> list[Movie]:
        """Поиск по подстроке названия. fragment подставляется как параметр."""
        rows = self._conn.execute(
            f"{self._SELECT} WHERE title LIKE ? ORDER BY title", (f"%{fragment}%",)
        ).fetchall()
        return [Movie.from_row(row) for row in rows]

    def top_by_rating(self, limit: int = 5) -> list[Movie]:
        rows = self._conn.execute(
            f"{self._SELECT} ORDER BY rating DESC LIMIT ?", (limit,)
        ).fetchall()
        return [Movie.from_row(row) for row in rows]

    def count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) AS cnt FROM movies").fetchone()
        return int(row["cnt"])

    def create(self, title: str, duration: int, rating: float, poster_path: str) -> int:
        cursor = self._conn.execute(
            "INSERT INTO movies (title, duration, rating, poster_path) VALUES (?, ?, ?, ?)",
            (title, duration, rating, poster_path),
        )
        return int(cursor.lastrowid)

    def update_rating(self, movie_id: int, rating: float) -> int:
        cursor = self._conn.execute(
            "UPDATE movies SET rating = ? WHERE id = ?", (rating, movie_id)
        )
        if cursor.rowcount == 0:
            raise EntityNotFoundError(f"Фильм id={movie_id} не найден")
        return cursor.rowcount

    def delete(self, movie_id: int) -> int:
        cursor = self._conn.execute("DELETE FROM movies WHERE id = ?", (movie_id,))
        if cursor.rowcount == 0:
            raise EntityNotFoundError(f"Фильм id={movie_id} не найден")
        return cursor.rowcount

    def recommendations(self, movie_id: int, limit: int = 5) -> list[Movie]:
        """Похожие фильмы: максимум общих жанров, затем выше рейтинг.

        Используется источником данных для кэш-слоя (cache-aside).
        """
        sql = """
            SELECT m.id, m.title, m.duration, m.rating, m.poster_path,
                   COUNT(mg2.genre_id) AS common_genres
            FROM movie_genres AS mg1
            JOIN movie_genres AS mg2
                 ON mg2.genre_id = mg1.genre_id AND mg2.movie_id <> mg1.movie_id
            JOIN movies AS m ON m.id = mg2.movie_id
            WHERE mg1.movie_id = ?
            GROUP BY m.id
            ORDER BY common_genres DESC, m.rating DESC
            LIMIT ?
        """
        rows = self._conn.execute(sql, (movie_id, limit)).fetchall()
        return [Movie.from_row(row) for row in rows]


class GenreRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def all(self) -> list[Genre]:
        rows = self._conn.execute("SELECT id, name FROM genres ORDER BY name").fetchall()
        return [Genre.from_row(row) for row in rows]

    def by_movie(self, movie_id: int) -> list[Genre]:
        rows = self._conn.execute(
            """
            SELECT g.id, g.name
            FROM genres AS g
            JOIN movie_genres AS mg ON mg.genre_id = g.id
            WHERE mg.movie_id = ?
            ORDER BY g.name
            """,
            (movie_id,),
        ).fetchall()
        return [Genre.from_row(row) for row in rows]


class HallRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def all(self) -> list[Hall]:
        rows = self._conn.execute("SELECT id, name, capacity FROM halls ORDER BY id").fetchall()
        return [Hall.from_row(row) for row in rows]

    def get(self, hall_id: int) -> Hall:
        row = self._conn.execute(
            "SELECT id, name, capacity FROM halls WHERE id = ?", (hall_id,)
        ).fetchone()
        if row is None:
            raise EntityNotFoundError(f"Зал id={hall_id} не найден")
        return Hall.from_row(row)

    def create(self, name: str, capacity: int) -> int:
        cursor = self._conn.execute(
            "INSERT INTO halls (name, capacity) VALUES (?, ?)", (name, capacity)
        )
        return int(cursor.lastrowid)


class ScreeningRepository:
    """Сеансы + операции продажи билетов (используются в транзакции)."""

    _SELECT = ("SELECT id, movie_id, hall_id, start_time, price, tickets_sold "
               "FROM screenings")

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def get(self, screening_id: int) -> Screening:
        row = self._conn.execute(f"{self._SELECT} WHERE id = ?", (screening_id,)).fetchone()
        if row is None:
            raise EntityNotFoundError(f"Сеанс id={screening_id} не найден")
        return Screening.from_row(row)

    def by_movie(self, movie_id: int) -> list[Screening]:
        rows = self._conn.execute(
            f"{self._SELECT} WHERE movie_id = ? ORDER BY start_time", (movie_id,)
        ).fetchall()
        return [Screening.from_row(row) for row in rows]

    def create(self, movie_id: int, hall_id: int, start_time: str,
               price: float, tickets_sold: int = 0) -> int:
        cursor = self._conn.execute(
            "INSERT INTO screenings (movie_id, hall_id, start_time, price, tickets_sold) "
            "VALUES (?, ?, ?, ?, ?)",
            (movie_id, hall_id, start_time, price, tickets_sold),
        )
        return int(cursor.lastrowid)

    def seats_left(self, screening_id: int) -> int:
        row = self._conn.execute(
            """
            SELECT h.capacity - s.tickets_sold AS seats_left
            FROM screenings AS s
            JOIN halls AS h ON h.id = s.hall_id
            WHERE s.id = ?
            """,
            (screening_id,),
        ).fetchone()
        if row is None:
            raise EntityNotFoundError(f"Сеанс id={screening_id} не найден")
        return int(row["seats_left"])

    def register_sale(self, screening_id: int, tickets: int) -> int:
        """Увеличивает счётчик проданных билетов (UPDATE)."""
        cursor = self._conn.execute(
            "UPDATE screenings SET tickets_sold = tickets_sold + ? WHERE id = ?",
            (tickets, screening_id),
        )
        if cursor.rowcount == 0:
            raise EntityNotFoundError(f"Сеанс id={screening_id} не найден")
        return cursor.rowcount

    def record_sale(self, screening_id: int, tickets: int, total_price: float) -> int:
        """Вставляет запись о продаже (INSERT) и возвращает её id."""
        cursor = self._conn.execute(
            "INSERT INTO ticket_sales (screening_id, tickets, total_price) VALUES (?, ?, ?)",
            (screening_id, tickets, total_price),
        )
        return int(cursor.lastrowid)

    def sales_count(self, screening_id: int) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS cnt FROM ticket_sales WHERE screening_id = ?",
            (screening_id,),
        ).fetchone()
        return int(row["cnt"])
