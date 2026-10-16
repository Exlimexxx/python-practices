from typing import Dict, List, Optional, TypeVar
from interfaces.repository import Repository

T = TypeVar("T")


class InMemoryRepository(Repository[T]):

    def __init__(self) -> None:
        self._storage: Dict[int, T] = {}

    def _get_id(self, entity: T) -> int:
        for attr in ["ticket_id", "session_id", "id"]:
            if hasattr(entity, attr):
                return getattr(entity, attr)
        raise AttributeError("Сущность не имеет поля идентификатора")

    def add(self, entity: T) -> None:
        entity_id = self._get_id(entity)
        self._storage[entity_id] = entity

    def get_by_id(self, entity_id: int) -> Optional[T]:
        return self._storage.get(entity_id)

    def get_all(self) -> List[T]:
        return list(self._storage.values())

    def delete(self, entity_id: int) -> None:
        if entity_id in self._storage:
            del self._storage[entity_id]