import json
import os
from typing import List, Optional, TypeVar
from dataclasses import asdict
from interfaces.repository import Repository

T = TypeVar("T")


class FileRepository(Repository[T]):

    def __init__(self, filename: str, entity_class: type) -> None:
        self.filename = filename
        self.entity_class = entity_class
        if not os.path.exists(self.filename):
            with open(self.filename, "w", encoding="utf-8") as f:
                json.dump([], f)

    def _load(self) -> List[dict]:
        with open(self.filename, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self, data: List[dict]) -> None:
        with open(self.filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def _get_id_attr(self) -> str:
        return (
            "ticket_id"
            if "Ticket" in self.entity_class.__name__
            else "session_id"
        )

    def add(self, entity: T) -> None:
        records = self._load()
        id_attr = self._get_id_attr()
        entity_dict = asdict(entity)
        records = [
            r for r in records if r.get(id_attr) != getattr(entity, id_attr)
        ]
        records.append(entity_dict)
        self._save(records)

    def get_by_id(self, entity_id: int) -> Optional[T]:
        records = self._load()
        id_attr = self._get_id_attr()
        for record in records:
            if record.get(id_attr) == entity_id:
                return self.entity_class(**record)
        return None

    def get_all(self) -> List[T]:
        records = self._load()
        return [self.entity_class(**record) for record in records]

    def delete(self, entity_id: int) -> None:
        records = self._load()
        id_attr = self._get_id_attr()
        records = [r for r in records if r.get(id_attr) != entity_id]
        self._save(records)