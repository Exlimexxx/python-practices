"""Базовый репозиторий с обобщёнными CRUD-операциями."""
from __future__ import annotations

from typing import Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Обобщённый репозиторий: create/read/list/update/delete для модели ModelT."""

    model: type[ModelT]

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, obj_id: int) -> ModelT | None:
        """Получить объект по первичному ключу или None."""
        return self.session.get(self.model, obj_id)

    def list_all(self) -> list[ModelT]:
        """Получить список всех объектов."""
        return list(self.session.scalars(select(self.model)).all())

    def add(self, obj: ModelT) -> ModelT:
        """Добавить объект в сессию и выполнить flush (INSERT без commit)."""
        self.session.add(obj)
        self.session.flush()
        return obj

    def update(self, obj: ModelT, **fields: object) -> ModelT:
        """Изменить переданные поля объекта и выполнить flush."""
        for name, value in fields.items():
            if not hasattr(obj, name):
                raise AttributeError(f"У модели {type(obj).__name__} нет поля {name!r}")
            setattr(obj, name, value)
        self.session.flush()
        return obj

    def delete(self, obj: ModelT) -> None:
        """Удалить объект из базы данных."""
        self.session.delete(obj)
        self.session.flush()

    def delete_by_id(self, obj_id: int) -> bool:
        """Удалить объект по id; вернуть True, если объект существовал."""
        obj = self.get_by_id(obj_id)
        if obj is None:
            return False
        self.delete(obj)
        return True

    def count(self) -> int:
        """Количество строк в таблице."""
        return int(self.session.scalar(select(func.count()).select_from(self.model)) or 0)
