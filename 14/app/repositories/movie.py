"""Репозиторий фильмов: весь доступ к БД сосредоточен здесь (п. 32 методички).

В router'ах SQL-запросов нет — только вызовы сервиса.
"""
from __future__ import annotations

import logging

from sqlalchemy import func, or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..exceptions import DatabaseError
from ..models.movie import Movie

logger = logging.getLogger(__name__)

#: Поля, по которым разрешена сортировка.
SORTABLE_FIELDS: frozenset[str] = frozenset(
    {"id", "title", "director", "year", "genre", "duration", "rating"}
)


class MovieRepository:
    """Класс-репозиторий: инкапсулирует запросы SQLAlchemy к таблице movies."""

    def __init__(self, db: Session) -> None:
        self._db = db

    # ------------------------------------------------------------------ CRUD
    def create(self, data: dict) -> Movie:
        """Создаёт фильм и сохраняет его в БД."""
        movie = Movie(**data)
        try:
            self._db.add(movie)
            self._db.commit()
            self._db.refresh(movie)
        except SQLAlchemyError as exc:  # noqa: BLE001
            self._db.rollback()
            logger.exception("Ошибка БД при создании фильма")
            raise DatabaseError("Не удалось сохранить фильм") from exc
        return movie

    def get(self, movie_id: int) -> Movie | None:
        """Возвращает фильм по id или None."""
        return self._db.get(Movie, movie_id)

    def list(
        self,
        *,
        genre: str | None = None,
        min_rating: float | None = None,
        year: int | None = None,
        query: str | None = None,
        sort: str = "id",
        order: str = "asc",
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Movie], int]:
        """Возвращает страницу фильмов и общее количество записей по фильтру."""
        stmt = select(Movie)
        stmt = self._apply_filters(stmt, genre=genre, min_rating=min_rating, year=year, query=query)
        try:
            total = self._db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
            column = getattr(Movie, sort)
            stmt = stmt.order_by(column.desc() if order == "desc" else column.asc())
            stmt = stmt.limit(limit).offset(offset)
            items = list(self._db.scalars(stmt).all())
        except SQLAlchemyError as exc:  # noqa: BLE001
            logger.exception("Ошибка БД при выборке фильмов")
            raise DatabaseError("Не удалось получить список фильмов") from exc
        return items, int(total)

    def _ci(self, column):
        """Регистронезависимое выражение для колонки (Unicode-aware).

        SQLite: используется зарегистрированная UDF casefold().
        Остальные СУБД (PostgreSQL): встроенный lower(), понимающий Unicode.
        """
        dialect = self._db.get_bind().dialect.name
        if dialect == "sqlite":
            return func.casefold(column)
        return func.lower(column)

    def _apply_filters(self, stmt, *, genre, min_rating, year, query):
        """Навешивает условия WHERE (используется списком и поиском)."""
        if genre:
            stmt = stmt.where(self._ci(Movie.genre) == genre.strip().casefold())
        if min_rating is not None:
            stmt = stmt.where(Movie.rating >= min_rating)
        if year is not None:
            stmt = stmt.where(Movie.year == year)
        if query:
            pattern = f"%{query.strip().casefold()}%"
            stmt = stmt.where(
                or_(
                    self._ci(Movie.title).like(pattern),
                    self._ci(Movie.director).like(pattern),
                    self._ci(Movie.description).like(pattern),
                )
            )
        return stmt

    def update(self, movie: Movie, data: dict) -> Movie:
        """Применяет изменения к фильму и сохраняет их."""
        for field, value in data.items():
            setattr(movie, field, value)
        try:
            self._db.commit()
            self._db.refresh(movie)
        except SQLAlchemyError as exc:  # noqa: BLE001
            self._db.rollback()
            logger.exception("Ошибка БД при обновлении фильма id=%s", movie.id)
            raise DatabaseError("Не удалось обновить фильм") from exc
        return movie

    def delete(self, movie: Movie) -> None:
        """Удаляет фильм из БД."""
        try:
            self._db.delete(movie)
            self._db.commit()
        except SQLAlchemyError as exc:  # noqa: BLE001
            self._db.rollback()
            logger.exception("Ошибка БД при удалении фильма id=%s", movie.id)
            raise DatabaseError("Не удалось удалить фильм") from exc

    # -------------------------------------------------------------- агрегаты
    def stats(self) -> dict:
        """Считает статистику по всем фильмам (п. 30 методички)."""
        try:
            total = int(self._db.scalar(select(func.count(Movie.id))) or 0)
            average_rating = self._db.scalar(select(func.avg(Movie.rating)))
            max_rating = self._db.scalar(select(func.max(Movie.rating)))
            min_rating = self._db.scalar(select(func.min(Movie.rating)))
            total_duration = int(self._db.scalar(select(func.coalesce(func.sum(Movie.duration), 0))) or 0)
            rows = self._db.execute(
                select(Movie.genre, func.count(Movie.id)).group_by(Movie.genre).order_by(Movie.genre)
            ).all()
        except SQLAlchemyError as exc:  # noqa: BLE001
            logger.exception("Ошибка БД при расчёте статистики")
            raise DatabaseError("Не удалось рассчитать статистику") from exc

        by_genre = [{"genre": genre, "count": int(count)} for genre, count in rows]
        return {
            "total": total,
            "average_rating": round(float(average_rating), 2) if average_rating is not None else None,
            "max_rating": round(float(max_rating), 2) if max_rating is not None else None,
            "min_rating": round(float(min_rating), 2) if min_rating is not None else None,
            "total_duration": total_duration,
            "by_genre": by_genre,
        }
