# -*- coding: utf-8 -*-
"""Модель предметной области «Кинотеатр» (лабораторная работа №10, вариант 4).

Модуль содержит dataclass Movie — ресурс REST API. Данные хранятся только
в памяти (см. repository.py): использование БД и ORM методичкой запрещено.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class Movie:
    """Фильм кинотеатра (шесть полей, поле id обязательно).

    :param id: уникальный идентификатор (назначается сервером)
    :param title: название фильма
    :param genre: жанр (например, «фантастика»)
    :param duration: длительность в минутах
    :param rating: рейтинг по десятибалльной шкале (0..10)
    :param price: стоимость билета, руб.
    """

    id: int
    title: str
    genre: str
    duration: int
    rating: float
    price: float

    def __post_init__(self) -> None:
        """Нормализует строковые поля (убирает лишние пробелы по краям)."""
        self.title = self.title.strip()
        self.genre = self.genre.strip()

    def to_dict(self) -> dict[str, Any]:
        """Сериализация объекта в JSON-совместимый словарь."""
        return {
            "id": self.id,
            "title": self.title,
            "genre": self.genre,
            "duration": self.duration,
            "rating": self.rating,
            "price": self.price,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Movie":
        """Создание объекта из словаря (используется в тестах и демонстрациях)."""
        return cls(
            id=int(data.get("id", 0)),
            title=str(data.get("title", "")),
            genre=str(data.get("genre", "")),
            duration=int(data["duration"]),
            rating=float(data["rating"]),
            price=float(data["price"]),
        )
