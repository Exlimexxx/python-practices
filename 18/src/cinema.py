"""Предметная модель, Repository и Service для тестирования кинотеатра."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class CinemaError(Exception):
    """Базовая ошибка предметной области."""


class ValidationError(CinemaError):
    pass


class NotFoundError(CinemaError):
    pass


class SeatAlreadyTakenError(CinemaError):
    pass


@dataclass(frozen=True)
class Movie:
    id: int
    title: str
    genre: str
    duration: int
    rating: float


@dataclass(frozen=True)
class Screening:
    id: int
    movie_id: int
    hall: str
    starts_at: str
    rows_count: int
    seats_per_row: int


@dataclass(frozen=True)
class Ticket:
    id: int
    screening_id: int
    row_no: int
    seat_no: int
    customer: str


class CinemaRepository:
    """SQLite-репозиторий; путь к тестовой БД передаётся при создании."""

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self.connection = sqlite3.connect(str(db_path), check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS movies(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              title TEXT NOT NULL UNIQUE,
              genre TEXT NOT NULL,
              duration INTEGER NOT NULL CHECK(duration BETWEEN 1 AND 400),
              rating REAL NOT NULL CHECK(rating BETWEEN 0 AND 10)
            );
            CREATE TABLE IF NOT EXISTS screenings(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              movie_id INTEGER NOT NULL REFERENCES movies(id), hall TEXT NOT NULL,
              starts_at TEXT NOT NULL, rows_count INTEGER NOT NULL,
              seats_per_row INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS tickets(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              screening_id INTEGER NOT NULL REFERENCES screenings(id),
              row_no INTEGER NOT NULL, seat_no INTEGER NOT NULL,
              customer TEXT NOT NULL,
              UNIQUE(screening_id,row_no,seat_no)
            );
            """
        )
        self.connection.commit()

    def add_movie(self, title: str, genre: str, duration: int, rating: float) -> Movie:
        cursor = self.connection.execute(
            "INSERT INTO movies(title,genre,duration,rating) VALUES(?,?,?,?)",
            (title, genre, duration, rating),
        )
        self.connection.commit()
        return self.get_movie(int(cursor.lastrowid))

    def get_movie(self, movie_id: int) -> Movie | None:
        row = self.connection.execute("SELECT * FROM movies WHERE id=?", (movie_id,)).fetchone()
        return Movie(**dict(row)) if row else None

    def list_movies(self) -> list[Movie]:
        return [Movie(**dict(row)) for row in self.connection.execute("SELECT * FROM movies ORDER BY id")]

    def update_movie(self, movie_id: int, fields: dict[str, Any]) -> bool:
        allowed = {"title", "genre", "duration", "rating"}
        if not fields or not set(fields).issubset(allowed):
            raise ValueError("Нет полей для изменения или есть неизвестное поле")
        keys = list(fields)
        values = [fields[k] for k in keys]
        cursor = self.connection.execute(
            f"UPDATE movies SET {', '.join(f'{key}=?' for key in keys)} WHERE id=?",
            [*values, movie_id],
        )
        self.connection.commit()
        return cursor.rowcount == 1

    def delete_movie(self, movie_id: int) -> bool:
        used = self.connection.execute("SELECT 1 FROM screenings WHERE movie_id=?", (movie_id,)).fetchone()
        if used:
            raise ValueError("Нельзя удалить фильм с существующими сеансами")
        cursor = self.connection.execute("DELETE FROM movies WHERE id=?", (movie_id,))
        self.connection.commit()
        return cursor.rowcount == 1

    def search_movies(self, query: str = "", genre: str | None = None) -> list[Movie]:
        # Python casefold корректно обрабатывает кириллицу; SQLite lower() — нет.
        items = [Movie(**dict(row)) for row in self.connection.execute("SELECT * FROM movies")]
        query_key = query.strip().casefold()
        genre_key = genre.strip().casefold() if genre else ""
        result = [movie for movie in items
                  if query_key in movie.title.casefold()
                  and (not genre_key or movie.genre.casefold() == genre_key)]
        return sorted(result, key=lambda movie: (-movie.rating, movie.title.casefold()))

    def create_screening(self, movie_id: int, hall: str, starts_at: str,
                         rows_count: int = 10, seats_per_row: int = 12) -> Screening:
        cursor = self.connection.execute(
            "INSERT INTO screenings(movie_id,hall,starts_at,rows_count,seats_per_row) VALUES(?,?,?,?,?)",
            (movie_id, hall, starts_at, rows_count, seats_per_row),
        )
        self.connection.commit()
        return self.get_screening(int(cursor.lastrowid))

    def get_screening(self, screening_id: int) -> Screening | None:
        row = self.connection.execute("SELECT * FROM screenings WHERE id=?", (screening_id,)).fetchone()
        return Screening(**dict(row)) if row else None

    def book_ticket(self, screening_id: int, row_no: int, seat_no: int, customer: str) -> Ticket:
        cursor = self.connection.execute(
            "INSERT INTO tickets(screening_id,row_no,seat_no,customer) VALUES(?,?,?,?)",
            (screening_id, row_no, seat_no, customer),
        )
        self.connection.commit()
        return Ticket(int(cursor.lastrowid), screening_id, row_no, seat_no, customer)

    def get_ticket(self, ticket_id: int) -> Ticket | None:
        row = self.connection.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)).fetchone()
        return Ticket(**dict(row)) if row else None

    def cancel_ticket(self, ticket_id: int) -> bool:
        cursor = self.connection.execute("DELETE FROM tickets WHERE id=?", (ticket_id,))
        self.connection.commit()
        return cursor.rowcount == 1

    def close(self) -> None:
        self.connection.close()


class CinemaService:
    """Сервис валидирует данные и реализует правила продажи билетов."""

    def __init__(self, repository: CinemaRepository) -> None:
        self.repository = repository

    def add_movie(self, title: str, genre: str, duration: int, rating: float) -> Movie:
        title, genre = title.strip(), genre.strip()
        if not title or not genre:
            raise ValidationError("Название и жанр обязательны")
        if not 1 <= int(duration) <= 400:
            raise ValidationError("Длительность должна быть в диапазоне 1..400")
        if not 0 <= float(rating) <= 10:
            raise ValidationError("Рейтинг должен быть в диапазоне 0..10")
        try:
            return self.repository.add_movie(title, genre, int(duration), float(rating))
        except sqlite3.IntegrityError as exc:
            raise ValidationError("Фильм с таким названием уже существует") from exc

    def get_movie(self, movie_id: int) -> Movie:
        if movie_id <= 0:
            raise ValidationError("ID должен быть положительным")
        movie = self.repository.get_movie(movie_id)
        if movie is None:
            raise NotFoundError("Фильм не найден")
        return movie

    def list_movies(self) -> list[Movie]:
        return self.repository.list_movies()

    def update_movie(self, movie_id: int, fields: dict[str, Any]) -> None:
        if "duration" in fields and not 1 <= int(fields["duration"]) <= 400:
            raise ValidationError("Некорректная длительность")
        if "rating" in fields and not 0 <= float(fields["rating"]) <= 10:
            raise ValidationError("Некорректный рейтинг")
        try:
            updated = self.repository.update_movie(movie_id, fields)
        except sqlite3.IntegrityError as exc:
            raise ValidationError("Конфликт данных фильма") from exc
        if not updated:
            raise NotFoundError("Фильм не найден")

    def delete_movie(self, movie_id: int) -> None:
        if not self.repository.delete_movie(movie_id):
            raise NotFoundError("Фильм не найден")

    def search_movies(self, query: str = "", genre: str | None = None) -> list[Movie]:
        return self.repository.search_movies(query, genre)

    def create_screening(self, movie_id: int, hall: str, starts_at: str,
                         rows_count: int = 10, seats_per_row: int = 12) -> Screening:
        if self.repository.get_movie(movie_id) is None:
            raise NotFoundError("Фильм для сеанса не найден")
        if not hall.strip() or rows_count <= 0 or seats_per_row <= 0:
            raise ValidationError("Параметры зала некорректны")
        return self.repository.create_screening(movie_id, hall, starts_at, rows_count, seats_per_row)

    def book_ticket(self, screening_id: int, row_no: int, seat_no: int, customer: str) -> Ticket:
        screening = self.repository.get_screening(screening_id)
        if screening is None:
            raise NotFoundError("Сеанс не найден")
        if not customer.strip():
            raise ValidationError("Не указано имя покупателя")
        if not 1 <= row_no <= screening.rows_count:
            raise ValidationError("Ряд вне диапазона")
        if not 1 <= seat_no <= screening.seats_per_row:
            raise ValidationError("Место вне диапазона")
        try:
            return self.repository.book_ticket(screening_id, row_no, seat_no, customer.strip())
        except sqlite3.IntegrityError as exc:
            raise SeatAlreadyTakenError("Место уже занято") from exc

    def cancel_ticket(self, ticket_id: int) -> None:
        if not self.repository.cancel_ticket(ticket_id):
            raise NotFoundError("Билет не найден")
