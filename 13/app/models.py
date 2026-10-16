"""Модели предметной области «Кинотеатр — фильмы» (вариант 4).

Документ коллекции movie содержит:
* простые поля: title, year, duration, rating, poster, status;
* вложенный документ: director ({name, country});
* массивы: genres, actors;
* массив вложенных документов: sessions (сеансы).

Все модели описаны через @dataclass и умеют преобразовываться в документ
MongoDB (to_document) и обратно (from_document).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, ClassVar

from .errors import SerializationError, ValidationError

#: Допустимые статусы фильма (поле-категория, требуемое методичкой).
ALLOWED_STATUSES: tuple[str, ...] = ("showing", "coming_soon", "archived")

#: Допустимые форматы сеанса.
ALLOWED_FORMATS: tuple[str, ...] = ("2D", "3D", "IMAX")


@dataclass
class Director:
    """Вложенный документ — режиссёр фильма."""

    name: str
    country: str

    def validate(self) -> None:
        if not self.name.strip():
            raise ValidationError("Имя режиссёра не может быть пустым")
        if not self.country.strip():
            raise ValidationError("Страна режиссёра не может быть пустой")


@dataclass
class Session:
    """Элемент массива sessions — описание сеанса."""

    date: str
    time: str
    hall: str
    price: float
    format: str = "2D"

    def validate(self) -> None:
        if self.format not in ALLOWED_FORMATS:
            raise ValidationError(f"Недопустимый формат сеанса: {self.format!r}")
        if self.price < 0:
            raise ValidationError("Цена билета не может быть отрицательной")
        if not self.hall.strip():
            raise ValidationError("Зал не может быть пустым")


@dataclass
class Movie:
    """Основная модель — фильм кинотеатра."""

    title: str
    director: Director
    year: int
    genres: list[str] = field(default_factory=list)
    actors: list[str] = field(default_factory=list)
    duration: int = 0
    rating: float = 0.0
    poster: str = ""
    sessions: list[Session] = field(default_factory=list)
    status: str = "showing"
    #: Идентификатор документа MongoDB; None — документ ещё не сохранён.
    id: Any = field(default=None, compare=False)
    #: Имя коллекции для наглядности.
    collection_name: ClassVar[str] = "movie"

    # ---------------------------------------------------------------- проверки
    def validate(self) -> "Movie":
        """Проверить корректность данных, вернуть self (удобно для цепочек)."""
        if not self.title.strip():
            raise ValidationError("Название фильма не может быть пустым")
        self.director.validate()
        if not (1888 <= self.year <= 2100):
            raise ValidationError(f"Некорректный год выпуска: {self.year}")
        if self.duration <= 0:
            raise ValidationError("Продолжительность должна быть положительной")
        if not (0.0 <= self.rating <= 10.0):
            raise ValidationError(f"Рейтинг должен быть в диапазоне 0..10, получено {self.rating}")
        if not self.genres:
            raise ValidationError("У фильма должен быть хотя бы один жанр")
        if self.status not in ALLOWED_STATUSES:
            raise ValidationError(f"Недопустимый статус: {self.status!r}")
        for session in self.sessions:
            session.validate()
        return self

    # ------------------------------------------------------------ сериализация
    def to_document(self) -> dict[str, Any]:
        """Преобразовать фильм в документ MongoDB."""
        self.validate()
        doc: dict[str, Any] = {
            "title": self.title,
            "director": {"name": self.director.name, "country": self.director.country},
            "year": self.year,
            "genres": list(self.genres),
            "actors": list(self.actors),
            "duration": self.duration,
            "rating": self.rating,
            "poster": self.poster,
            "sessions": [asdict(s) for s in self.sessions],
            "status": self.status,
        }
        if self.id is not None:
            doc["_id"] = self.id
        return doc

    @classmethod
    def from_document(cls, doc: dict[str, Any]) -> "Movie":
        """Построить модель из документа MongoDB."""
        if not isinstance(doc, dict):
            raise SerializationError(f"Ожидался документ, получено {type(doc).__name__}")
        try:
            director_raw = doc.get("director") or {}
            if isinstance(director_raw, str):  # поддержка «плоского» вида
                director = Director(name=director_raw, country="—")
            else:
                director = Director(
                    name=str(director_raw.get("name", "")),
                    country=str(director_raw.get("country", "—")),
                )
            sessions = [
                Session(
                    date=str(s.get("date", "")),
                    time=str(s.get("time", "")),
                    hall=str(s.get("hall", "")),
                    price=float(s.get("price", 0)),
                    format=str(s.get("format", "2D")),
                )
                for s in (doc.get("sessions") or [])
            ]
            return cls(
                title=str(doc.get("title", "")),
                director=director,
                year=int(doc.get("year", 0)),
                genres=[str(g) for g in (doc.get("genres") or [])],
                actors=[str(a) for a in (doc.get("actors") or [])],
                duration=int(doc.get("duration", 0)),
                rating=float(doc.get("rating", 0.0)),
                poster=str(doc.get("poster", "")),
                sessions=sessions,
                status=str(doc.get("status", "showing")),
                id=doc.get("_id"),
            )
        except (TypeError, ValueError, KeyError) as exc:  # ошибки сериализации
            raise SerializationError(f"Не удалось разобрать документ: {exc}") from exc

    def summary(self) -> str:
        """Короткая строка для консольного вывода."""
        return (
            f"{self.title!r} ({self.year}), реж. {self.director.name}, "
            f"{', '.join(self.genres)}, {self.duration} мин, рейтинг {self.rating}, "
            f"статус {self.status}"
        )
