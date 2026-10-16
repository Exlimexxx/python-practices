"""Сервис фильмов: бизнес-логика + работа с кэшем (п. 15, 33, 34 методички)."""
from __future__ import annotations

import asyncio
import logging

from ..cache import CacheBackend, cache_key_movie
from ..exceptions import InvalidQueryError, MovieNotFoundError
from ..repositories.movie import SORTABLE_FIELDS, MovieRepository
from ..schemas.movie import (
    MovieCreate,
    MovieListResponse,
    MovieResponse,
    MovieStats,
    MovieUpdate,
)

logger = logging.getLogger(__name__)

ALLOWED_ORDERS = {"asc", "desc"}


class MovieService:
    """Бизнес-логика над репозиторием фильмов."""

    def __init__(self, repository: MovieRepository, cache: CacheBackend) -> None:
        self._repo = repository
        self._cache = cache

    # ------------------------------------------------------------ валидация
    @staticmethod
    def _validate_sorting(sort: str, order: str) -> None:
        """Проверяет параметры сортировки, иначе HTTP 400 (не 422)."""
        if sort not in SORTABLE_FIELDS:
            raise InvalidQueryError(
                f"Недопустимое поле сортировки '{sort}'",
                {"allowed": sorted(SORTABLE_FIELDS)},
            )
        if order not in ALLOWED_ORDERS:
            raise InvalidQueryError(
                f"Недопустимое направление сортировки '{order}'",
                {"allowed": sorted(ALLOWED_ORDERS)},
            )

    # ----------------------------------------------------------------- чтение
    def list_movies(
        self,
        *,
        genre: str | None = None,
        min_rating: float | None = None,
        year: int | None = None,
        sort: str = "id",
        order: str = "asc",
        limit: int = 20,
        offset: int = 0,
    ) -> MovieListResponse:
        """Возвращает отфильтрованный, отсортированный и постраничный список."""
        self._validate_sorting(sort, order)
        items, total = self._repo.list(
            genre=genre,
            min_rating=min_rating,
            year=year,
            sort=sort,
            order=order,
            limit=limit,
            offset=offset,
        )
        return MovieListResponse(
            items=[MovieResponse.model_validate(m) for m in items],
            total=total,
            limit=limit,
            offset=offset,
        )

    def search_movies(self, q: str, limit: int = 20, offset: int = 0) -> MovieListResponse:
        """Полнотекстовый поиск по названию/режиссёру/описанию (п. 21)."""
        if not q or not q.strip():
            raise InvalidQueryError("Поисковый запрос q не может быть пустым")
        items, total = self._repo.list(query=q.strip(), sort="id", order="asc", limit=limit, offset=offset)
        return MovieListResponse(
            items=[MovieResponse.model_validate(m) for m in items],
            total=total,
            limit=limit,
            offset=offset,
        )

    def movies_by_genre(self, genre: str, limit: int = 20, offset: int = 0) -> MovieListResponse:
        """Фильмы конкретного жанра (специальная операция варианта)."""
        if not genre or not genre.strip():
            raise InvalidQueryError("Жанр не может быть пустым")
        items, total = self._repo.list(genre=genre.strip(), sort="rating", order="desc", limit=limit, offset=offset)
        return MovieListResponse(
            items=[MovieResponse.model_validate(m) for m in items],
            total=total,
            limit=limit,
            offset=offset,
        )

    async def get_movie(self, movie_id: int) -> MovieResponse:
        """Возвращает фильм по id, используя кэш (cache-aside, п. 33).

        Это асинхронный метод: сначала проверяется кэш, и только при промахе
        выполняется запрос в БД, после чего результат кладётся в кэш.
        """
        key = cache_key_movie(movie_id)
        cached = await self._cache.get(key)
        if cached is not None:
            logger.info("cache HIT %s", key)
            return MovieResponse.model_validate(cached)

        logger.info("cache MISS %s -> запрос в БД", key)
        movie = self._repo.get(movie_id)
        if movie is None:
            raise MovieNotFoundError(movie_id)

        response = MovieResponse.model_validate(movie)
        await self._cache.set(key, response.model_dump(mode="json"))
        return response

    async def get_stats(self) -> MovieStats:
        """Статистика по фильмам.

        Асинхронный обработчик: синхронный доступ к SQLAlchemy вынесен
        в отдельный поток через asyncio.to_thread, чтобы не блокировать event loop.
        """
        raw = await asyncio.to_thread(self._repo.stats)
        return MovieStats.model_validate(raw)

    # ----------------------------------------------------------- изменения
    async def create_movie(self, data: MovieCreate) -> MovieResponse:
        """Создаёт фильм."""
        movie = self._repo.create(data.model_dump())
        logger.info("Создан фильм id=%s '%s'", movie.id, movie.title)
        return MovieResponse.model_validate(movie)

    async def replace_movie(self, movie_id: int, data: MovieCreate) -> MovieResponse:
        """PUT: полная замена объекта."""
        movie = self._repo.get(movie_id)
        if movie is None:
            raise MovieNotFoundError(movie_id)
        updated = self._repo.update(movie, data.model_dump())
        await self._invalidate(movie_id)
        return MovieResponse.model_validate(updated)

    async def patch_movie(self, movie_id: int, data: MovieUpdate) -> MovieResponse:
        """PATCH: изменяются только явно переданные поля."""
        movie = self._repo.get(movie_id)
        if movie is None:
            raise MovieNotFoundError(movie_id)
        changes = data.model_dump(exclude_unset=True)
        if not changes:
            raise InvalidQueryError("Тело PATCH не содержит полей для изменения")
        updated = self._repo.update(movie, changes)
        await self._invalidate(movie_id)
        return MovieResponse.model_validate(updated)

    async def delete_movie(self, movie_id: int) -> None:
        """Удаляет фильм и инвалидирует кэш."""
        movie = self._repo.get(movie_id)
        if movie is None:
            raise MovieNotFoundError(movie_id)
        self._repo.delete(movie)
        await self._invalidate(movie_id)
        logger.info("Удалён фильм id=%s", movie_id)

    async def _invalidate(self, movie_id: int) -> None:
        """Сбрасывает кэш конкретного фильма (п. 34 методички)."""
        await self._cache.delete(cache_key_movie(movie_id))
        logger.info("cache INVALIDATE movie:%s", movie_id)
