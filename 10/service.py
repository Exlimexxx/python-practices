# -*- coding: utf-8 -*-
"""Service — бизнес-логика REST API кинотеатра.

Слой отвечает за:
* валидацию входных данных (через schemas.py);
* фильтрацию и сортировку списка фильмов;
* специализированную операцию «фильмы по жанру»;
* проверку существования объекта (404 Not Found).

HTTP-слой (routes.py) вызывает только методы этого класса и не содержит
собственной бизнес-логики — это требование методички.
"""
from __future__ import annotations

import logging
from typing import Any

from exceptions import NotFoundError, ValidationError
from models import Movie
from repository import MovieRepository
from schemas import validate_movie_payload

LOGGER = logging.getLogger(__name__)


class MovieService:
    """Бизнес-логика работы с фильмами."""

    def __init__(self, repository: MovieRepository) -> None:
        self._repository = repository

    @property
    def repository(self) -> MovieRepository:
        """Доступ к хранилищу (используется в тестах)."""
        return self._repository

    # --- чтение -----------------------------------------------------------
    def list_movies(
        self,
        *,
        genre: str | None = None,
        min_rating: float | None = None,
        max_price: float | None = None,
        sort: str | None = None,
        order: str = "asc",
    ) -> list[Movie]:
        """Возвращает список фильмов с фильтрацией и сортировкой.

        :param genre: фильтр по жанру (без учёта регистра)
        :param min_rating: фильтр по минимальному рейтингу
        :param max_price: фильтр по максимальной цене билета
        :param sort: поле сортировки (price, rating, title, duration)
        :param order: направление сортировки (asc или desc)
        """
        movies = self._repository.get_all()

        if genre:
            genre_lower = genre.strip().lower()
            movies = [movie for movie in movies if movie.genre.lower() == genre_lower]
        if min_rating is not None:
            movies = [movie for movie in movies if movie.rating >= min_rating]
        if max_price is not None:
            movies = [movie for movie in movies if movie.price <= max_price]

        if sort:
            if sort == "title":
                key = lambda movie: movie.title.lower()  # noqa: E731
            else:
                key = lambda movie: getattr(movie, sort)  # noqa: E731
            movies = sorted(movies, key=key, reverse=(order == "desc"))

        LOGGER.debug(
            "list_movies: найдено %d записей (genre=%s, min_rating=%s, max_price=%s, sort=%s, order=%s)",
            len(movies), genre, min_rating, max_price, sort, order,
        )
        return movies

    def get_movie(self, movie_id: int) -> Movie:
        """Возвращает фильм по id или поднимает NotFoundError (404)."""
        movie = self._repository.get_by_id(movie_id)
        if movie is None:
            raise NotFoundError(f"Фильм с id={movie_id} не найден")
        return movie

    def get_movies_by_genre(self, genre: str | None) -> dict[str, Any]:
        """Специализированная операция: фильмы заданного жанра.

        Возвращает словарь с жанром, количеством найденных фильмов и списком.
        Фильмы отсортированы по убыванию рейтинга.

        :raises ValidationError: если параметр genre не передан или пуст
        """
        if genre is None or not str(genre).strip():
            raise ValidationError("Параметр 'genre' обязателен и не может быть пустым")
        genre_value = str(genre).strip()
        movies = self.list_movies(genre=genre_value, sort="rating", order="desc")
        return {
            "genre": genre_value,
            "count": len(movies),
            "movies": [movie.to_dict() for movie in movies],
        }

    # --- изменение --------------------------------------------------------
    def create_movie(self, data: Any) -> Movie:
        """Создаёт фильм, предварительно проверив данные.

        :raises ValidationError: если данные некорректны (объект не создаётся)
        """
        payload = validate_movie_payload(data)
        movie = Movie(id=0, **payload)
        created = self._repository.create(movie)
        LOGGER.info("Создан фильм id=%s: %s", created.id, created.title)
        return created

    def replace_movie(self, movie_id: int, data: Any) -> Movie:
        """PUT: полное изменение фильма.

        :raises NotFoundError: если фильма нет (404)
        :raises ValidationError: если данные некорректны (400)
        """
        self.get_movie(movie_id)
        payload = validate_movie_payload(data)
        updated = self._repository.update(movie_id, Movie(id=movie_id, **payload))
        if updated is None:  # защитная проверка, практически недостижима
            raise NotFoundError(f"Фильм с id={movie_id} не найден")
        LOGGER.info("Изменён (PUT) фильм id=%s", movie_id)
        return updated

    def patch_movie(self, movie_id: int, data: Any) -> Movie:
        """PATCH: частичное изменение фильма.

        Изменяются только переданные поля; итоговый объект повторно
        валидируется целиком.

        :raises NotFoundError: если фильма нет (404)
        :raises ValidationError: если данные некорректны (400)
        """
        current = self.get_movie(movie_id)
        payload = validate_movie_payload(data, partial=True)
        merged = current.to_dict()
        merged.pop("id", None)
        merged.update(payload)
        validated = validate_movie_payload(merged)
        updated = self._repository.update(movie_id, Movie(id=movie_id, **validated))
        if updated is None:
            raise NotFoundError(f"Фильм с id={movie_id} не найден")
        LOGGER.info("Изменён (PATCH) фильм id=%s, поля: %s", movie_id, ", ".join(sorted(payload)))
        return updated

    def delete_movie(self, movie_id: int) -> None:
        """Удаляет фильм.

        :raises NotFoundError: если фильма нет (404)
        """
        if not self._repository.delete(movie_id):
            raise NotFoundError(f"Фильм с id={movie_id} не найден")
        LOGGER.info("Удалён фильм id=%s", movie_id)

    # --- дополнительно ----------------------------------------------------
    def get_statistics(self) -> dict[str, Any]:
        """Небольшая сводка по каталогу (демонстрирует работу Service)."""
        movies = self._repository.get_all()
        if not movies:
            return {"count": 0, "average_rating": 0.0, "average_price": 0.0}
        return {
            "count": len(movies),
            "average_rating": round(sum(movie.rating for movie in movies) / len(movies), 2),
            "average_price": round(sum(movie.price for movie in movies) / len(movies), 2),
        }
