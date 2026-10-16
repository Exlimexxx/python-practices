"""Каталог фильмов кинотеатра и функция его загрузки в БД.

Модуль намеренно отделён от seed.py: здесь только данные предметной
области (фильмы и их жанры), а seed.py добавляет залы и сеансы.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class MovieSeed:
    """Описание фильма для первичного наполнения БД."""

    title: str
    duration: int
    rating: float
    poster_path: str
    genres: tuple[str, ...]


#: Минимум 10 фильмов (по заданию) — здесь 12.
MOVIES: tuple[MovieSeed, ...] = (
    MovieSeed("Начало", 148, 8.8, "/static/posters/poster_1.svg",
              ("фантастика", "боевик", "триллер")),
    MovieSeed("Интерстеллар", 169, 8.6, "/static/posters/poster_2.svg",
              ("фантастика", "драма")),
    MovieSeed("Тёмный рыцарь", 152, 9.0, "/static/posters/poster_3.svg",
              ("боевик", "триллер", "драма")),
    MovieSeed("Матрица", 136, 8.7, "/static/posters/poster_1.svg",
              ("фантастика", "боевик")),
    MovieSeed("Побег из Шоушенка", 142, 9.3, "/static/posters/poster_2.svg",
              ("драма", "криминал")),
    MovieSeed("Форрест Гамп", 142, 8.8, "/static/posters/poster_3.svg",
              ("драма", "комедия")),
    MovieSeed("Криминальное чтиво", 154, 8.9, "/static/posters/poster_1.svg",
              ("криминал", "драма")),
    MovieSeed("Бойцовский клуб", 139, 8.8, "/static/posters/poster_2.svg",
              ("драма", "триллер")),
    MovieSeed("Гладиатор", 155, 8.5, "/static/posters/poster_3.svg",
              ("боевик", "драма")),
    MovieSeed("Король Лев", 88, 8.5, "/static/posters/poster_1.svg",
              ("анимация", "драма")),
    MovieSeed("Властелин колец: Братство Кольца", 178, 8.9, "/static/posters/poster_2.svg",
              ("фантастика", "драма")),
    MovieSeed("Паразиты", 132, 8.5, "/static/posters/poster_3.svg",
              ("драма", "триллер")),
)


def seed_movies(conn: sqlite3.Connection) -> tuple[int, int, int]:
    """Наполняет таблицы movies, genres и movie_genres.

    Возвращает кортеж (фильмов, жанров, связей N:M).
    Используются ТОЛЬКО параметризованные запросы.
    """
    genre_names = sorted({genre for movie in MOVIES for genre in movie.genres})

    conn.executemany(
        "INSERT INTO genres (name) VALUES (?)",
        [(name,) for name in genre_names],
    )
    conn.executemany(
        "INSERT INTO movies (title, duration, rating, poster_path) VALUES (?, ?, ?, ?)",
        [(m.title, m.duration, m.rating, m.poster_path) for m in MOVIES],
    )

    genre_id = {row["name"]: row["id"] for row in conn.execute("SELECT id, name FROM genres")}
    movie_id = {row["title"]: row["id"] for row in conn.execute("SELECT id, title FROM movies")}

    links = [(movie_id[m.title], genre_id[genre]) for m in MOVIES for genre in m.genres]
    conn.executemany(
        "INSERT INTO movie_genres (movie_id, genre_id) VALUES (?, ?)",
        links,
    )
    return len(MOVIES), len(genre_names), len(links)
