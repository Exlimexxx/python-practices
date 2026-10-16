# -*- coding: utf-8 -*-
"""Repository — хранилище фильмов в памяти (без БД и ORM).

Слой отвечает только за доступ к данным: создание, чтение, изменение и
удаление объектов Movie. Никакой бизнес-логики и валидации здесь нет —
это задача service.py.
"""
from __future__ import annotations

import threading
from dataclasses import replace
from typing import Iterable

from models import Movie


class MovieRepository:
    """Потокобезопасное хранилище фильмов на основе словаря {id: Movie}."""

    def __init__(self, movies: Iterable[Movie] | None = None) -> None:
        self._by_id: dict[int, Movie] = {}
        self._next_id: int = 1
        self._lock = threading.RLock()
        for movie in movies or ():
            self._add_initial(movie)

    # --- внутренние методы ------------------------------------------------
    def _add_initial(self, movie: Movie) -> None:
        """Добавляет предустановленный фильм, сохраняя его id."""
        with self._lock:
            self._by_id[movie.id] = movie
            self._next_id = max(self._next_id, movie.id + 1)

    # --- публичный интерфейс ---------------------------------------------
    def get_all(self) -> list[Movie]:
        """Возвращает все фильмы, отсортированные по id."""
        with self._lock:
            return sorted(self._by_id.values(), key=lambda movie: movie.id)

    def get_by_id(self, movie_id: int) -> Movie | None:
        """Возвращает фильм по id или None, если его нет."""
        with self._lock:
            return self._by_id.get(movie_id)

    def exists(self, movie_id: int) -> bool:
        """Проверяет наличие фильма с указанным id."""
        with self._lock:
            return movie_id in self._by_id

    def create(self, movie: Movie) -> Movie:
        """Сохраняет новый фильм, назначая следующий свободный id."""
        with self._lock:
            new_id = self._next_id
            self._next_id += 1
            stored = replace(movie, id=new_id)
            self._by_id[new_id] = stored
            return stored

    def update(self, movie_id: int, movie: Movie) -> Movie | None:
        """Полностью заменяет фильм с указанным id (id сохраняется)."""
        with self._lock:
            if movie_id not in self._by_id:
                return None
            stored = replace(movie, id=movie_id)
            self._by_id[movie_id] = stored
            return stored

    def delete(self, movie_id: int) -> bool:
        """Удаляет фильм; возвращает True, если запись существовала."""
        with self._lock:
            return self._by_id.pop(movie_id, None) is not None

    def count(self) -> int:
        """Количество фильмов в хранилище."""
        with self._lock:
            return len(self._by_id)

    def clear(self) -> None:
        """Полностью очищает хранилище (используется в тестах)."""
        with self._lock:
            self._by_id.clear()
            self._next_id = 1


def seed_movies() -> list[Movie]:
    """Начальный набор фильмов кинотеатра (шесть записей, шесть жанров)."""
    return [
        Movie(id=1, title="Интерстеллар", genre="фантастика", duration=169, rating=8.6, price=550.0),
        Movie(id=2, title="Начало", genre="фантастика", duration=148, rating=8.8, price=500.0),
        Movie(id=3, title="Одержимость", genre="драма", duration=107, rating=8.5, price=450.0),
        Movie(id=4, title="Дэдпул", genre="боевик", duration=108, rating=8.0, price=400.0),
        Movie(id=5, title="Головоломка", genre="анимация", duration=95, rating=8.2, price=350.0),
        Movie(id=6, title="Паразиты", genre="триллер", duration=132, rating=8.6, price=520.0),
    ]
