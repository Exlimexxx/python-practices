"""Базовый репозиторий с общими операциями доступа к данным."""
from __future__ import annotations

from typing import Generic, Sequence, TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)
DEFAULT_LIMIT = 100


class SqlAlchemyRepository(Generic[ModelT]):
    """Общие CRUD-операции для одной сущности.

    Репозиторий выполняет только запросы и не принимает решений о правилах
    предметной области: проверки остаются в сервисном слое.
    """

    model: type[ModelT]

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, entity: ModelT) -> ModelT:
        self.session.add(entity)
        self.session.flush()
        return entity

    def get(self, entity_id: int) -> ModelT | None:
        return self.session.get(self.model, entity_id)

    def delete(self, entity: ModelT) -> None:
        self.session.delete(entity)
        self.session.flush()

    def list_all(self, *, limit: int = DEFAULT_LIMIT, offset: int = 0) -> Sequence[ModelT]:
        statement = (
            select(self.model).order_by(self.model.id).limit(limit).offset(offset)  # type: ignore[attr-defined]
        )
        return self.session.scalars(statement).all()

    def count(self) -> int:
        return int(self.session.scalar(select(func.count()).select_from(self.model)) or 0)
