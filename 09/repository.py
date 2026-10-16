"""Слой хранения (этап 3 методички).

Хранилище полностью в памяти процесса: словарь id -> Student.
Данные защищены RLock, поэтому репозиторий безопасно используется
несколькими потоками одновременно (этап 6 и 11 -- несколько клиентов).

Наружу выдаются копии объектов: сетевой код не может случайно
изменить состояние хранилища, не пройдя через сервис.
"""

from __future__ import annotations

import threading
from dataclasses import replace
from typing import Callable, Dict, Iterable, List, Optional

from exceptions import ConflictError, NotFoundError, ValidationError
from models import Student


class StudentRepository:
    """Репозиторий студентов с операциями add/get/get_all/update/delete."""

    def __init__(self, initial: Iterable[Student] | None = None) -> None:
        self._items: Dict[int, Student] = {}
        self._lock = threading.RLock()
        self._next_id: int = 1
        for student in initial or ():
            self.add(student)

    # ------------------------------------------------------------------
    # служебные операции
    # ------------------------------------------------------------------
    def count(self) -> int:
        """Количество объектов в хранилище."""
        with self._lock:
            return len(self._items)

    def exists(self, student_id: int) -> bool:
        """Проверяет наличие объекта с указанным id."""
        with self._lock:
            return student_id in self._items

    def next_id(self) -> int:
        """Значение следующего свободного идентификатора."""
        with self._lock:
            return self._next_id

    def _reserve_id(self) -> int:
        """Выдаёт новый идентификатор (вызывается под блокировкой)."""
        new_id = self._next_id
        self._next_id += 1
        return new_id

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    def add(self, student: Student) -> Student:
        """Добавляет студента; при id=0 идентификатор присваивается автоматически."""
        if not isinstance(student, Student):
            raise ValidationError("Репозиторий принимает только объекты Student")

        with self._lock:
            prepared = replace(student, grades=list(student.grades))
            if prepared.id == 0:
                prepared = replace(prepared, id=self._reserve_id())
            else:
                if prepared.id in self._items:
                    raise ConflictError(
                        f"Студент с id={prepared.id} уже существует",
                        "conflict",
                    )
                if prepared.id >= self._next_id:
                    self._next_id = prepared.id + 1
            prepared.validate()
            self._items[prepared.id] = prepared
            return replace(prepared, grades=list(prepared.grades))

    def get(self, student_id: int) -> Student:
        """Возвращает студента по id; иначе NotFoundError."""
        with self._lock:
            student = self._items.get(int(student_id))
            if student is None:
                raise NotFoundError(f"Студент с id={student_id} не найден")
            return replace(student, grades=list(student.grades))

    def get_all(self) -> List[Student]:
        """Все студенты, отсортированные по идентификатору."""
        with self._lock:
            students = [replace(item, grades=list(item.grades)) for item in self._items.values()]
        return sorted(students, key=lambda item: item.id)

    def find(self, predicate: Callable[[Student], bool]) -> List[Student]:
        """Возвращает всех студентов, удовлетворяющих условию."""
        return [student for student in self.get_all() if predicate(student)]

    def update(self, student: Student) -> Student:
        """Полностью заменяет существующего студента."""
        if not isinstance(student, Student):
            raise ValidationError("Репозиторий принимает только объекты Student")

        with self._lock:
            if student.id not in self._items:
                raise NotFoundError(f"Студент с id={student.id} не найден")
            student.validate()
            self._items[student.id] = replace(student, grades=list(student.grades))
            return replace(student, grades=list(student.grades))

    def delete(self, student_id: int) -> Student:
        """Удаляет студента и возвращает удалённый объект."""
        with self._lock:
            student = self._items.pop(int(student_id), None)
            if student is None:
                raise NotFoundError(f"Студент с id={student_id} не найден")
            return replace(student, grades=list(student.grades))

    def clear(self) -> None:
        """Полностью очищает хранилище (используется в тестах)."""
        with self._lock:
            self._items.clear()
            self._next_id = 1
