"""Сервисный слой: бизнес-логика кинотеатра.

Содержит:
* продажу билетов в транзакции (COMMIT при успехе, ROLLBACK при ошибке);
* получение рекомендаций через кэш (cache-aside).
"""
from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import asdict, dataclass

from cache import CacheBackend
from db import transaction
from repository import (
    EntityNotFoundError,
    GenreRepository,
    HallRepository,
    Movie,
    MovieRepository,
    ScreeningRepository,
)

logger = logging.getLogger("cinema.service")

#: Время жизни кэша рекомендаций — 60 секунд (по заданию).
RECOMMENDATIONS_TTL = 60
#: Шаблон ключа кэша рекомендаций для фильма.
RECOMMENDATIONS_KEY = "recommendations:movie:{movie_id}"


class CinemaError(RuntimeError):
    """Базовая ошибка бизнес-логики кинотеатра."""


class SeatUnavailableError(CinemaError):
    """Недостаточно свободных мест на сеансе."""


@dataclass(frozen=True)
class TicketSale:
    """Результат успешной продажи билетов."""

    sale_id: int
    screening_id: int
    movie_title: str
    start_time: str
    tickets: int
    total_price: float
    seats_left: int


@dataclass(frozen=True)
class Recommendation:
    """Фильм-рекомендация (то, что кладётся в кэш в виде JSON)."""

    id: int
    title: str
    rating: float
    poster_path: str


class CinemaService:
    def __init__(self, conn: sqlite3.Connection, cache: CacheBackend) -> None:
        self._conn = conn
        self._cache = cache
        self._movies = MovieRepository(conn)
        self._screenings = ScreeningRepository(conn)
        self._halls = HallRepository(conn)
        self._genres = GenreRepository(conn)

    # ------------------------------------------------------------------
    # Транзакция: продажа билетов
    # ------------------------------------------------------------------
    def sell_ticket(self, screening_id: int, tickets: int = 1) -> TicketSale:
        """Продаёт билеты в одной транзакции.

        Шаги: проверка сеанса -> проверка свободных мест -> вставка продажи
        (ticket_sales) -> увеличение счётчика tickets_sold.
        Любая ошибка приводит к ROLLBACK (ни продажи, ни изменения счётчика).
        """
        if tickets <= 0:
            raise ValueError("Количество билетов должно быть положительным")

        with transaction(self._conn):
            screening = self._screenings.get(screening_id)
            movie = self._movies.get(screening.movie_id)
            seats_before = self._screenings.seats_left(screening_id)
            if seats_before < tickets:
                raise SeatUnavailableError(
                    f"На сеанс {screening_id} («{movie.title}») осталось "
                    f"{seats_before} мест, запрошено {tickets}"
                )
            total_price = round(screening.price * tickets, 2)
            sale_id = self._screenings.record_sale(screening_id, tickets, total_price)
            self._screenings.register_sale(screening_id, tickets)
            seats_left = seats_before - tickets

        logger.info("Продажа #%s: %s, %s бил., %.2f руб., осталось мест: %s",
                    sale_id, movie.title, tickets, total_price, seats_left)
        return TicketSale(
            sale_id=sale_id,
            screening_id=screening_id,
            movie_title=movie.title,
            start_time=screening.start_time,
            tickets=tickets,
            total_price=total_price,
            seats_left=seats_left,
        )

    # ------------------------------------------------------------------
    # Кэш рекомендаций (cache-aside)
    # ------------------------------------------------------------------
    def _cache_key(self, movie_id: int) -> str:
        return RECOMMENDATIONS_KEY.format(movie_id=movie_id)

    def recommendations(self, movie_id: int, limit: int = 5) -> list[Recommendation]:
        """Сначала смотрит в кэш; при промахе читает SQLite и кладёт JSON в кэш."""
        key = self._cache_key(movie_id)
        cached = self._cache.get(key)
        if cached is not None:
            self._cache.incr("stats:cache_hits")
            logger.info("CACHE HIT  %s (TTL=%s сек.)", key, self._cache.ttl(key))
            return [Recommendation(**item) for item in json.loads(cached)]

        logger.info("CACHE MISS %s — читаем рекомендации из SQLite", key)
        movies = self._movies.recommendations(movie_id, limit=limit)
        payload = json.dumps(
            [{"id": m.id, "title": m.title, "rating": m.rating, "poster_path": m.poster_path}
             for m in movies],
            ensure_ascii=False,
        )
        self._cache.set(key, payload, ttl=RECOMMENDATIONS_TTL)
        self._cache.incr("stats:cache_misses")
        return [Recommendation(**item) for item in json.loads(payload)]

    def invalidate_recommendations(self, movie_id: int) -> bool:
        """Инвалидация кэша: удаляем ключ, чтобы пересчитать рекомендации."""
        key = self._cache_key(movie_id)
        removed = self._cache.delete(key)
        logger.info("CACHE INVALIDATE %s -> %s", key, "удалён" if removed else "ключа не было")
        return removed

    def movie_with_genres(self, movie_id: int) -> tuple[Movie, list[str]]:
        movie = self._movies.get(movie_id)
        genres = [g.name for g in self._genres.by_movie(movie_id)]
        return movie, genres

    def seats_left(self, screening_id: int) -> int:
        return self._screenings.seats_left(screening_id)
