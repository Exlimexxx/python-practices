"""ORM-модель фильма (сущность Movie, вариант 4)."""
from __future__ import annotations

from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class Movie(Base):
    """Таблица movies: фильмы кинотеатра."""

    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, doc="Идентификатор")
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True, doc="Название")
    director: Mapped[str] = mapped_column(String(200), nullable=False, doc="Режиссёр")
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True, doc="Год выпуска")
    genre: Mapped[str] = mapped_column(String(100), nullable=False, index=True, doc="Жанр")
    duration: Mapped[int] = mapped_column(Integer, nullable=False, doc="Продолжительность, мин")
    rating: Mapped[float] = mapped_column(Float, nullable=False, index=True, doc="Рейтинг 0..10")
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True, doc="Описание")

    def __repr__(self) -> str:  # pragma: no cover - отладочное представление
        return f"<Movie id={self.id} title={self.title!r} year={self.year}>"
