from typing import Protocol, TypeVar, List, Optional

T = TypeVar("T")


class Repository(Protocol[T]):

    def add(self, entity: T) -> None:
        ...

    def get_by_id(self, entity_id: int) -> Optional[T]:
        ...

    def get_all(self) -> List[T]:
        ...

    def delete(self, entity_id: int) -> None:
        ...