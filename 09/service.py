"""Сервисный слой -- бизнес-логика (этап 4 методички).

Схема вызовов::

    Client -> Server -> Service -> Repository

Сетевой код (server.py) не обращается к репозиторию напрямую: он лишь
передаёт данные сюда. Здесь выполняются создание, поиск, изменение,
удаление, фильтрация и специализированные операции варианта 4:
average_grade (средний балл студента) и groups (сводка по группам).
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional

from exceptions import NotFoundError, ValidationError
from models import Student, parse_int
from repository import StudentRepository


@dataclass
class GroupSummary:
    """Сводка по одной учебной группе (дополнительная операция)."""

    group: str
    students_count: int
    average_grade: float
    best_student: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "group": self.group,
            "students_count": self.students_count,
            "average_grade": self.average_grade,
            "best_student": self.best_student,
        }


class StudentService:
    """Бизнес-логика предметной области "Университет"."""

    def __init__(self, repository: Optional[StudentRepository] = None) -> None:
        self.repository: StudentRepository = repository or StudentRepository()
        self._started_at: float = time.time()
        self.completed_commands: int = 0

    # ==================================================================
    # базовые (CRUD) операции
    # ==================================================================
    def create_student(self, data: Mapping[str, Any]) -> Student:
        """Создаёт студента из данных запроса."""
        student = Student.from_dict(data)
        created = self.repository.add(student)
        self.completed_commands += 1
        return created

    def get_student(self, student_id: Any) -> Student:
        """Возвращает студента по идентификатору."""
        identifier = parse_int(student_id, "id", minimum=0)
        student = self.repository.get(identifier)
        self.completed_commands += 1
        return student

    def update_student(self, student_id: Any, data: Mapping[str, Any]) -> Student:
        """Частично изменяет студента (переданные поля заменяются)."""
        if not isinstance(data, Mapping):
            raise ValidationError("Данные для изменения должны быть объектом JSON")

        identifier = parse_int(student_id, "id", minimum=0)
        current = self.repository.get(identifier)

        allowed = {"name", "group", "grades", "email", "year", "status"}
        unknown = set(data) - allowed
        if unknown:
            raise ValidationError(
                "Неизвестные поля для изменения: " + ", ".join(sorted(unknown))
            )

        merged: Dict[str, Any] = current.to_dict()
        merged.update({key: value for key, value in data.items() if value is not None})
        merged["id"] = identifier

        updated = Student.from_dict(merged)
        saved = self.repository.update(updated)
        self.completed_commands += 1
        return saved

    def delete_student(self, student_id: Any) -> Student:
        """Удаляет студента."""
        identifier = parse_int(student_id, "id", minimum=0)
        removed = self.repository.delete(identifier)
        self.completed_commands += 1
        return removed

    # ==================================================================
    # фильтрация и специализированные операции
    # ==================================================================
    def list_students(self, filters: Optional[Mapping[str, Any]] = None) -> List[Student]:
        """Возвращает список студентов с необязательной фильтрацией.

        Поддерживаемые фильтры: group, status, year, name_contains,
        min_average, sort_by (id|name|group|average), limit.
        """
        filters = dict(filters or {})
        students = self.repository.get_all()

        group = filters.get("group")
        if group:
            students = [s for s in students if s.group.lower() == str(group).lower()]

        status = filters.get("status")
        if status:
            students = [s for s in students if s.status == str(status).lower()]

        if filters.get("year") is not None:
            year = parse_int(filters["year"], "year", minimum=1, maximum=6)
            students = [s for s in students if s.year == year]

        name_contains = filters.get("name_contains")
        if name_contains:
            needle = str(name_contains).lower()
            students = [s for s in students if needle in s.name.lower()]

        if filters.get("min_average") is not None:
            try:
                threshold = float(filters["min_average"])
            except (TypeError, ValueError):
                raise ValidationError("Фильтр 'min_average' должен быть числом")
            students = [s for s in students if s.average >= threshold]

        sort_by = str(filters.get("sort_by", "id"))
        if sort_by not in {"id", "name", "group", "average", "year"}:
            raise ValidationError(f"Недопустимое поле сортировки: {sort_by}")
        students = sorted(students, key=lambda s: getattr(s, sort_by if sort_by != "average" else "average"))

        if filters.get("limit") is not None:
            limit = parse_int(filters["limit"], "limit", minimum=1)
            students = students[:limit]

        self.completed_commands += 1
        return students

    def average_grade(self, student_id: Any) -> Dict[str, Any]:
        """Специализированная команда варианта 4: средний балл студента."""
        student = self.get_student(student_id)
        grades = list(student.grades)
        return {
            "id": student.id,
            "name": student.name,
            "group": student.group,
            "grades": grades,
            "grades_count": len(grades),
            "average_grade": student.average,
            "min_grade": min(grades),
            "max_grade": max(grades),
        }

    def group_summary(self, data: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
        """Сводка по группам: количество студентов и средний балл."""
        data = dict(data or {})
        students = self.repository.get_all()
        target = data.get("group")
        if target:
            students = [s for s in students if s.group.lower() == str(target).lower()]
            if not students:
                raise NotFoundError(f"В группе {target!r} нет студентов")

        totals: Dict[str, List[Student]] = {}
        for student in students:
            totals.setdefault(student.group, []).append(student)

        summaries: List[GroupSummary] = []
        for group, members in sorted(totals.items()):
            average = round(sum(s.average for s in members) / len(members), 2)
            best = max(members, key=lambda s: s.average)
            summaries.append(
                GroupSummary(
                    group=group,
                    students_count=len(members),
                    average_grade=average,
                    best_student=best.name,
                )
            )

        self.completed_commands += 1
        return {
            "groups_count": len(summaries),
            "groups": [summary.to_dict() for summary in summaries],
        }

    def status(self) -> Dict[str, Any]:
        """Состояние сервера (используется и по TCP, и по UDP)."""
        students = self.repository.get_all()
        groups = sorted({student.group for student in students})
        average = (
            round(sum(s.average for s in students) / len(students), 2) if students else 0.0
        )
        return {
            "server": "running",
            "transport": "TCP",
            "protocol": "newline-delimited JSON",
            "students_count": len(students),
            "groups": groups,
            "average_grade": average,
            "uptime_seconds": round(time.time() - self._started_at, 2),
            "completed_commands": self.completed_commands,
        }

    # ==================================================================
    # демонстрационные данные
    # ==================================================================
    def seed_demo_data(self) -> int:
        """Наполняет хранилище тремя студентами для наглядных демонстраций."""
        demo_students = [
            Student(
                id=0,
                name="Иванов Иван Иванович",
                group="ИУ7-31Б",
                grades=[5, 4, 5, 5],
                email="ivanov@bmstu.ru",
                year=2,
                status="active",
            ),
            Student(
                id=0,
                name="Петрова Анна Сергеевна",
                group="ИУ7-31Б",
                grades=[4, 4, 3, 5],
                email="petrova@bmstu.ru",
                year=2,
                status="active",
            ),
            Student(
                id=0,
                name="Сидоров Пётр Алексеевич",
                group="ИУ7-32Б",
                grades=[3, 4, 3],
                email="sidorov@bmstu.ru",
                year=2,
                status="academic_leave",
            ),
        ]
        for student in demo_students:
            self.repository.add(student)
        return len(demo_students)
