# -*- coding: utf-8 -*-
"""Тесты Repository (2+ теста по требованиям методички)."""
from __future__ import annotations

from models import Movie
from repository import MovieRepository, seed_movies


def test_create_assigns_incremental_id() -> None:
    """Новому фильму назначается следующий свободный идентификатор."""
    repository = MovieRepository()
    first = repository.create(Movie(id=0, title="Дюна", genre="фантастика", duration=155, rating=8.3, price=600.0))
    second = repository.create(Movie(id=0, title="Соул", genre="анимация", duration=100, rating=8.1, price=380.0))

    assert first.id == 1
    assert second.id == 2
    assert repository.count() == 2


def test_get_all_get_by_id_and_delete() -> None:
    """Чтение списка, чтение по id и удаление записи."""
    repository = MovieRepository(seed_movies())

    assert [movie.id for movie in repository.get_all()] == [1, 2, 3, 4, 5, 6]
    movie = repository.get_by_id(1)
    assert movie is not None
    assert movie.title == "Интерстеллар"
    assert repository.get_by_id(999) is None

    assert repository.delete(1) is True
    assert repository.get_by_id(1) is None
    assert repository.delete(1) is False


def test_update_replaces_object_but_keeps_id() -> None:
    """Обновление заменяет объект, сохраняя идентификатор."""
    repository = MovieRepository(seed_movies())

    updated = repository.update(
        2,
        Movie(id=0, title="Начало (переиздание)", genre="фантастика", duration=150, rating=9.0, price=640.0),
    )

    assert updated is not None
    assert updated.id == 2
    assert repository.get_by_id(2).title == "Начало (переиздание)"  # type: ignore[union-attr]
    assert repository.update(999, updated) is None
