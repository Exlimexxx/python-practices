"""MongoRepository — слой доступа к MongoDB.

Класс инкапсулирует работу с коллекцией movie: CRUD, фильтрацию, проекции,
сортировку, агрегацию и управление индексами. Работает как с настоящим
PyMongo-клиентом, так и с in-memory реализацией (одинаковый API).
"""
from __future__ import annotations

import logging
from typing import Any, Iterable

from .errors import InvalidIdentifierError, NotFoundError, SerializationError
from .models import Movie

logger = logging.getLogger(__name__)


def normalize_id(raw: Any) -> Any:
    """Привести идентификатор к типу, пригодному для запроса MongoDB."""
    if raw is None or raw == "":
        raise InvalidIdentifierError("Идентификатор не задан")
    if isinstance(raw, int):
        return raw
    text = str(raw).strip()
    # ObjectId из 24 hex-символов
    if len(text) == 24:
        try:
            from bson import ObjectId

            return ObjectId(text)
        except Exception:  # noqa: BLE001 - bson может отсутствовать
            return text
    try:
        return int(text)
    except ValueError:
        return text


class MongoRepository:
    """Репозиторий фильмов поверх коллекции MongoDB."""

    def __init__(self, collection: Any, collection_name: str = "movie") -> None:
        self.collection = collection
        self.collection_name = collection_name
        self._indexes: list[str] = []

    # --------------------------------------------------------------- индексы
    def ensure_indexes(self) -> list[str]:
        """Создать индексы, ускоряющие реальные запросы приложения."""
        # 1) Составной индекс (genres, rating) — ускоряет фильтр по жанру с
        #    сортировкой по рейтингу (самый частый сценарий поиска).
        self._indexes.append(self.collection.create_index([("genres", 1), ("rating", -1)], name="genres_rating"))
        # 2) Индекс по вложенному полю director.name — ускоряет поиск фильмов
        #    конкретного режиссёра.
        self._indexes.append(self.collection.create_index("director.name", name="director_name"))
        # 3) Индекс по году — ускоряет диапазонные запросы и сортировку по году.
        self._indexes.append(self.collection.create_index([("year", -1)], name="year_desc"))
        logger.info("Индексы созданы: %s", self._indexes)
        return list(self._indexes)

    def index_information(self) -> dict[str, Any]:
        return dict(self.collection.index_information())

    # ------------------------------------------------------------------ CRUD
    def create(self, movie: Movie) -> Any:
        """Добавить фильм, вернуть _id созданного документа."""
        document = movie.to_document()
        result = self.collection.insert_one(document)
        movie.id = result.inserted_id
        logger.info("Создан фильм %r c _id=%s", movie.title, result.inserted_id)
        return result.inserted_id

    def create_many(self, movies: Iterable[Movie]) -> list[Any]:
        return [self.create(movie) for movie in movies]

    def get_document(self, movie_id: Any) -> dict[str, Any]:
        """Получить документ по идентификатору или бросить NotFoundError."""
        key = normalize_id(movie_id)
        document = self.collection.find_one({"_id": key})
        if document is None:
            raise NotFoundError(f"Фильм с _id={movie_id!r} не найден")
        return document

    def get(self, movie_id: Any) -> Movie:
        """Получить модель Movie по идентификатору."""
        return Movie.from_document(self.get_document(movie_id))

    def find(
        self,
        query: dict[str, Any] | None = None,
        projection: dict[str, Any] | None = None,
        sort: Any = None,
        limit: int = 0,
        skip: int = 0,
    ) -> list[dict[str, Any]]:
        """Найти документы по условию с проекцией, сортировкой и лимитом."""
        cursor = self.collection.find(query or {}, projection, sort=sort, limit=limit, skip=skip)
        return list(cursor)

    def find_movies(self, query: dict[str, Any] | None = None, **kwargs: Any) -> list[Movie]:
        return [Movie.from_document(doc) for doc in self.find(query, **kwargs)]

    def find_one(self, query: dict[str, Any]) -> dict[str, Any] | None:
        return self.collection.find_one(query)

    def update(self, movie_id: Any, changes: dict[str, Any]) -> bool:
        """Обновить поля документа через $set. True — документ изменён."""
        if not changes:
            raise SerializationError("Пустой набор изменений")
        key = normalize_id(movie_id)
        result = self.collection.update_one({"_id": key}, {"$set": dict(changes)})
        modified = bool(getattr(result, "matched_count", 0) or getattr(result, "modified_count", 0))
        logger.info("update _id=%s изменений=%s", movie_id, modified)
        return modified

    def replace(self, movie: Movie) -> bool:
        """Полностью заменить документ (кроме защищённого _id)."""
        if movie.id is None:
            raise InvalidIdentifierError("У модели не задан _id")
        key = normalize_id(movie.id)
        document = movie.to_document()
        document.pop("_id", None)
        result = self.collection.update_one({"_id": key}, {"$set": document})
        return bool(getattr(result, "matched_count", 0) or getattr(result, "modified_count", 0))

    def delete(self, movie_id: Any) -> bool:
        """Удалить документ по идентификатору."""
        key = normalize_id(movie_id)
        result = self.collection.delete_one({"_id": key})
        deleted = getattr(result, "deleted_count", 0) > 0
        logger.info("delete _id=%s удалено=%s", movie_id, deleted)
        return deleted

    def delete_many(self, query: dict[str, Any]) -> int:
        result = self.collection.delete_many(query)
        return int(getattr(result, "deleted_count", 0))

    def count(self, query: dict[str, Any] | None = None) -> int:
        return int(self.collection.count_documents(query or {}))

    def distinct(self, field: str, query: dict[str, Any] | None = None) -> list[Any]:
        return list(self.collection.distinct(field, query or {}))

    # --------------------------------------------------------- агрегация
    def aggregate(self, pipeline: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return list(self.collection.aggregate(pipeline))
