from typing import Dict, List, Optional, TypeVar
from interfaces.repository import Repository

T = TypeVar("T")


class InMemoryRepository(Repository[T]):
    """LSP: Универсальный репозиторий в памяти."""

    def __init__(self) -> None:
        self._storage: Dict[int, T] = {}

    def add(self, entity: T) -> None:
        # Предполагаем наличие атрибута _id в сущностях
        attr_name = [a for a in dir(entity) if a.endswith("_id")][0]
        entity_id = getattr(entity, attr_name)
        self._storage[entity_id] = entity

    def get_by_id(self, entity_id: int) -> Optional[T]:
        return self._storage.get(entity_id)

    def get_all(self) -> List[T]:
        return list(self._storage.values())