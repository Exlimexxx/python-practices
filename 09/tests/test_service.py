"""Тесты бизнес-логики (этап 12: минимум 2 теста Service)."""

from __future__ import annotations

import pytest

from exceptions import NotFoundError, ValidationError
from repository import StudentRepository
from service import StudentService


def build_service() -> StudentService:
    """Сервис с пустым репозиторием."""
    return StudentService(StudentRepository())


def test_create_student_from_dict() -> None:
    """Создание студента из данных протокола."""
    service = build_service()

    student = service.create_student(
        {
            "name": "Иванов Иван Иванович",
            "group": "ИУ7-31Б",
            "grades": [5, 4, 5],
            "email": "ivanov@bmstu.ru",
            "year": 2,
        }
    )

    assert student.id == 1
    assert student.status == "active"
    assert service.repository.count() == 1


def test_create_student_missing_fields_raises_validation() -> None:
    """Отсутствие обязательных полей -- ValidationError."""
    service = build_service()

    with pytest.raises(ValidationError):
        service.create_student({"name": "Без группы"})


def test_create_student_with_invalid_grades_raises_validation() -> None:
    """Оценка вне диапазона 2..5 недопустима."""
    service = build_service()

    with pytest.raises(ValidationError):
        service.create_student(
            {"name": "Иванов Иван", "group": "ИУ7-31Б", "grades": [5, 9]}
        )


def test_average_grade_special_command() -> None:
    """Специализированная команда average_grade считает средний балл."""
    service = build_service()
    student = service.create_student(
        {"name": "Петрова Анна Сергеевна", "group": "ИУ7-31Б", "grades": [5, 4, 4, 3]}
    )

    result = service.average_grade(student.id)

    assert result["average_grade"] == 4.0
    assert result["grades_count"] == 4
    assert result["min_grade"] == 3
    assert result["max_grade"] == 5


def test_average_grade_for_missing_student_raises_not_found() -> None:
    """Средний балл несуществующего студента -- NotFoundError."""
    service = build_service()

    with pytest.raises(NotFoundError):
        service.average_grade(12345)


def test_update_student_partial_changes() -> None:
    """update_student() меняет только переданные поля."""
    service = build_service()
    student = service.create_student(
        {"name": "Сидоров Пётр Алексеевич", "group": "ИУ7-31Б", "grades": [3, 3, 3]}
    )

    updated = service.update_student(student.id, {"grades": [5, 5, 5], "year": 3})

    assert updated.name == "Сидоров Пётр Алексеевич"
    assert updated.grades == [5, 5, 5]
    assert updated.year == 3


def test_update_student_unknown_field_raises_validation() -> None:
    """Неизвестное поле при изменении -- ValidationError."""
    service = build_service()
    student = service.create_student(
        {"name": "Сидоров Пётр Алексеевич", "group": "ИУ7-31Б", "grades": [3, 3, 3]}
    )

    with pytest.raises(ValidationError):
        service.update_student(student.id, {"salary": 100000})


def test_filter_students_by_group_and_average() -> None:
    """Фильтрация по группе, статусу и минимальному среднему баллу."""
    service = build_service()
    service.create_student(
        {
            "name": "Иванов Иван Иванович",
            "group": "ИУ7-31Б",
            "grades": [5, 5, 5],
            "status": "active",
        }
    )
    service.create_student(
        {
            "name": "Петрова Анна Сергеевна",
            "group": "ИУ7-32Б",
            "grades": [3, 3, 3],
            "status": "active",
        }
    )
    service.create_student(
        {
            "name": "Сидоров Пётр Алексеевич",
            "group": "ИУ7-31Б",
            "grades": [4, 4, 4],
            "status": "academic_leave",
        }
    )

    only_group = service.list_students({"group": "ИУ7-31Б"})
    assert [student.name for student in only_group] == [
        "Иванов Иван Иванович",
        "Сидоров Пётр Алексеевич",
    ]

    best = service.list_students({"min_average": 4.5})
    assert [student.name for student in best] == ["Иванов Иван Иванович"]

    on_leave = service.list_students({"status": "academic_leave"})
    assert len(on_leave) == 1


def test_delete_student_and_status() -> None:
    """Удаление и сводка состояния сервера."""
    service = build_service()
    first = service.create_student(
        {"name": "Иванов Иван Иванович", "group": "ИУ7-31Б", "grades": [5, 5, 5]}
    )
    service.seed_demo_data()

    removed = service.delete_student(first.id)
    status = service.status()

    assert removed.id == first.id
    assert status["students_count"] == 3
    assert status["groups"] == ["ИУ7-31Б", "ИУ7-32Б"]


def test_group_summary() -> None:
    """Сводка по группам (дополнительная команда groups)."""
    service = build_service()
    service.seed_demo_data()

    result = service.group_summary()

    assert result["groups_count"] == 2
    assert result["groups"][0]["group"] == "ИУ7-31Б"
    assert result["groups"][0]["students_count"] == 2
