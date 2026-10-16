"""Тесты MongoDB-части: подключение, CRUD, запросы, агрегация, проекции."""
from __future__ import annotations

import pytest

from app.errors import InvalidIdentifierError, NotFoundError, ValidationError
from app.models import Director, Movie
from app.mongodb import connect_mongo
from conftest import make_movie


def test_connection_to_mongodb() -> None:
    """Проверка подключения: получаем базу и считаем документы."""
    database, mode, _error = connect_mongo("mongodb://127.0.0.1:27017", "cinema_test")
    assert mode in ("mongodb", "memory")
    assert database["movie"].count_documents({}) >= 0


def test_create_document(repo) -> None:
    """Добавление документа."""
    movie = make_movie(title="Создание")
    inserted_id = repo.create(movie)
    assert inserted_id is not None
    assert repo.count({}) == 1
    assert repo.get(inserted_id).title == "Создание"


def test_read_document(repo) -> None:
    """Получение документа по _id."""
    inserted_id = repo.create(make_movie(title="Чтение"))
    loaded = repo.get(inserted_id)
    assert loaded.title == "Чтение"
    assert loaded.genres == ["драма", "фантастика"]


def test_update_document(repo) -> None:
    """Изменение документа."""
    inserted_id = repo.create(make_movie(title="Обновление"))
    assert repo.update(inserted_id, {"rating": 9.1, "status": "archived"})
    updated = repo.get(inserted_id)
    assert updated.rating == 9.1
    assert updated.status == "archived"


def test_delete_document(repo) -> None:
    """Удаление документа."""
    inserted_id = repo.create(make_movie(title="Удаление"))
    assert repo.delete(inserted_id) is True
    with pytest.raises(NotFoundError):
        repo.get(inserted_id)


def test_filter_by_genre(repo) -> None:
    """Фильтрация по элементу массива genres."""
    repo.create(make_movie(title="Драма", genre="драма"))
    repo.create(make_movie(title="Комедия", genre="комедия"))
    found = repo.find({"genres": "драма"})
    assert len(found) == 1
    assert found[0]["title"] == "Драма"


def test_filter_by_nested_field(repo) -> None:
    """Запрос по вложенному полю director.name."""
    repo.create(make_movie(title="Вложенный"))
    found = repo.find({"director.name": "Тестовый Режиссёр"})
    assert len(found) == 1


def test_filter_by_array_element(repo) -> None:
    """Запрос по элементу массива actors."""
    repo.create(make_movie(title="Массив"))
    assert len(repo.find({"actors": "Актёр Один"})) == 1
    assert len(repo.find({"actors": "Неизвестный актёр"})) == 0


def test_projection(repo) -> None:
    """Проекция: в результате только запрошенные поля."""
    repo.create(make_movie(title="Проекция"))
    docs = repo.find({}, projection={"title": 1, "rating": 1, "_id": 0})
    assert set(docs[0].keys()) == {"title", "rating"}


def test_aggregation_group_by_genre(repo) -> None:
    """Агрегация: количество фильмов по жанрам."""
    repo.create(make_movie(title="A", genre="драма"))
    repo.create(make_movie(title="B", genre="комедия"))
    repo.create(make_movie(title="C", genre="комедия"))
    result = repo.aggregate(
        [{"$unwind": "$genres"}, {"$group": {"_id": "$genres", "count": {"$sum": 1}}}, {"$sort": {"count": -1}}]
    )
    mapping = {row["_id"]: row["count"] for row in result}
    assert mapping["комедия"] == 2
    assert mapping["драма"] == 1


def test_invalid_and_missing_identifier(repo) -> None:
    """Некорректный идентификатор и отсутствующий документ."""
    with pytest.raises(InvalidIdentifierError):
        repo.get_document("")
    with pytest.raises(NotFoundError):
        repo.get_document("ffffffffffffffffffffffff")


def test_validation_error_on_bad_movie(repo) -> None:
    """Некорректные данные не попадают в хранилище."""
    bad = Movie(
        title="Плохой",
        director=Director(name="Режиссёр", country="США"),
        year=2020,
        genres=["драма"],
        duration=0,
        rating=20.0,
        status="showing",
    )
    with pytest.raises(ValidationError):
        repo.create(bad)
    assert repo.count({}) == 0
