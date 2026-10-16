"""Тесты слоя доступа к данным (repository)."""
from __future__ import annotations

import sqlite3

import pytest

from repository import (
    EntityNotFoundError,
    GenreRepository,
    HallRepository,
    MovieRepository,
    ScreeningRepository,
)


def test_seed_contains_at_least_10_movies(conn) -> None:
    assert MovieRepository(conn).count() >= 10


def test_get_returns_dataclass_with_fields(conn) -> None:
    movie = MovieRepository(conn).get(1)
    assert movie.id == 1
    assert movie.title == "Начало"
    assert movie.duration > 0
    assert 0 <= movie.rating <= 10


def test_get_unknown_movie_raises(conn) -> None:
    with pytest.raises(EntityNotFoundError):
        MovieRepository(conn).get(9999)


def test_search_uses_parameter_and_blocks_sql_injection(conn) -> None:
    repo = MovieRepository(conn)
    assert repo.search("Начало")[0].title == "Начало"
    # Классическая инъекция: если бы строка склеивалась, вернулись бы все фильмы.
    assert repo.search("' OR '1'='1") == []
    assert repo.search("Начало'; DROP TABLE movies;--") == []
    assert repo.count() >= 10  # таблица на месте


def test_unique_title_constraint(conn) -> None:
    repo = MovieRepository(conn)
    with pytest.raises(sqlite3.IntegrityError):
        repo.create("Начало", 100, 5.0, "/static/posters/poster_1.svg")


def test_check_constraint_rejects_bad_duration(conn) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO movies (title, duration, rating, poster_path) VALUES (?, ?, ?, ?)",
            ("Плохой фильм", 0, 5.0, "/x.svg"),
        )


def test_foreign_key_is_enforced(conn) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO screenings (movie_id, hall_id, start_time, price) VALUES (?, ?, ?, ?)",
            (9999, 1, "2030-01-01 10:00:00", 100.0),
        )


def test_movie_has_genres_via_nm_table(conn) -> None:
    genres = {g.name for g in GenreRepository(conn).by_movie(1)}
    assert genres == {"фантастика", "боевик", "триллер"}


def test_seats_left_uses_join_with_halls(conn) -> None:
    screenings = ScreeningRepository(conn)
    # Сеанс id=5: фильм «Форрест Гамп» (movie_id=6), Зал 3 «VIP» на 30 мест,
    # продано 18 билетов -> свободно 12.
    assert screenings.seats_left(5) == 30 - 18
    assert screenings.get(5).movie_id == 6


def test_register_sale_updates_counter(conn) -> None:
    screenings = ScreeningRepository(conn)
    before = screenings.get(9).tickets_sold
    screenings.register_sale(9, 3)
    assert screenings.get(9).tickets_sold == before + 3


def test_halls_repository(conn) -> None:
    halls = HallRepository(conn)
    assert len(halls.all()) >= 3
    new_id = halls.create("Зал 9 «Тестовый»", 10)
    assert halls.get(new_id).capacity == 10
