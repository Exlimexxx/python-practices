# -*- coding: utf-8 -*-
"""Тесты Service: валидация, фильтрация, сортировка, спец. операция."""
from __future__ import annotations

import pytest

from exceptions import NotFoundError, ValidationError
from service import MovieService


def test_list_movies_filter_by_genre_and_min_rating(service: MovieService) -> None:
    """Фильтрация по двум параметрам: genre и min_rating."""
    by_genre = service.list_movies(genre="фантастика")
    assert {movie.title for movie in by_genre} == {"Интерстеллар", "Начало"}

    by_rating = service.list_movies(min_rating=8.6)
    assert len(by_rating) == 3
    assert all(movie.rating >= 8.6 for movie in by_rating)


def test_list_movies_filter_by_max_price_and_sorting(service: MovieService) -> None:
    """Фильтрация по цене и сортировка минимум по двум полям."""
    by_price = service.list_movies(max_price=450.0, sort="price", order="desc")
    prices = [movie.price for movie in by_price]
    assert prices == sorted(prices, reverse=True)
    assert all(price <= 450.0 for price in prices)

    titles = [movie.title for movie in service.list_movies(sort="title", order="asc")]
    assert titles == sorted(titles)


def test_create_movie_assigns_id_and_validates(service: MovieService) -> None:
    """Создание фильма и отказ при некорректных данных."""
    created = service.create_movie(
        {"title": "  Дюна  ", "genre": "фантастика", "duration": 155, "rating": 8.3, "price": 600}
    )
    assert created.id == 7
    assert created.title == "Дюна"
    assert isinstance(created.price, float)

    with pytest.raises(ValidationError):
        service.create_movie({"title": " ", "genre": "", "duration": -5, "rating": 11, "price": -1})
    with pytest.raises(ValidationError):
        service.create_movie({"title": "Только название"})

    assert service.repository.count() == 7  # некорректные объекты не созданы


def test_get_and_delete_movie_not_found(service: MovieService) -> None:
    """Обращение к отсутствующему объекту даёт NotFoundError."""
    with pytest.raises(NotFoundError):
        service.get_movie(999)
    with pytest.raises(NotFoundError):
        service.delete_movie(999)


def test_patch_changes_only_provided_fields(service: MovieService) -> None:
    """PATCH изменяет только переданные поля."""
    updated = service.patch_movie(1, {"price": 700.0, "rating": 9.1})

    assert updated.price == 700.0
    assert updated.rating == 9.1
    assert updated.title == "Интерстеллар"
    assert updated.duration == 169


def test_get_movies_by_genre_special_operation(service: MovieService) -> None:
    """Специализированная операция: фильмы по жанру."""
    result = service.get_movies_by_genre("фантастика")

    assert result["genre"] == "фантастика"
    assert result["count"] == 2
    assert [movie["title"] for movie in result["movies"]] == ["Начало", "Интерстеллар"]  # сортировка по рейтингу

    with pytest.raises(ValidationError):
        service.get_movies_by_genre("")


def test_statistics_returns_average_values(service: MovieService) -> None:
    """Дополнительный метод бизнес-логики: сводная статистика каталога."""
    statistics = service.get_statistics()

    assert statistics["count"] == 6
    assert statistics["average_rating"] == pytest.approx(8.45, abs=0.01)
    assert statistics["average_price"] == pytest.approx(461.67, abs=0.01)
