from typing import Protocol, TypeVar, List, Optional

T = TypeVar("T")


class Repository(Protocol[T]):
    """ISP: Узкий интерфейс для базовых операций с хранилищем."""

    def add(self, entity: T) -> None:
        ...

    def get_by_id(self, entity_id: int) -> Optional[T]:
        ...

    def get_all(self) -> List[T]:
        ...