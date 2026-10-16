"""Тесты слоя хранения (этап 12: минимум 2 теста Repository)."""

from __future__ import annotations

import pytest

from exceptions import ConflictError, NotFoundError, ValidationError
from models import Student
from repository import StudentRepository


def make_student(student_id: int = 0, name: str = "Иванов Иван Иванович") -> Student:
    """Фабрика тестовых студентов."""
    return Student(
        id=student_id,
        name=name,
        group="ИУ7-31Б",
        grades=[5, 4, 5],
        email="test@bmstu.ru",
        year=2,
        status="active",
    )


def test_add_assigns_id_and_get_returns_copy() -> None:
    """add() присваивает id при 0 и get() возвращает независимую копию."""
    repository = StudentRepository()
    created = repository.add(make_student())

    assert created.id == 1
    assert repository.count() == 1

    fetched = repository.get(1)
    fetched.grades.append(2)  # изменение копии не должно влиять на хранилище
    assert repository.get(1).grades == [5, 4, 5]


def test_add_duplicate_id_raises_conflict() -> None:
    """Повторный id приводит к ConflictError."""
    repository = StudentRepository()
    repository.add(make_student(student_id=7))

    with pytest.raises(ConflictError):
        repository.add(make_student(student_id=7))


def test_get_missing_student_raises_not_found() -> None:
    """Запрос отсутствующего объекта -- NotFoundError."""
    repository = StudentRepository()

    with pytest.raises(NotFoundError):
        repository.get(999)


def test_update_existing_student() -> None:
    """update() заменяет объект, а не добавляет новый."""
    repository = StudentRepository()
    created = repository.add(make_student())
    changed = created.copy_with(group="ИУ7-32Б", grades=[3, 3, 3])

    updated = repository.update(changed)

    assert updated.group == "ИУ7-32Б"
    assert repository.count() == 1
    assert repository.get(created.id).average == 3.0


def test_delete_removes_student() -> None:
    """delete() удаляет объект и возвращает его; повторное удаление -- ошибка."""
    repository = StudentRepository()
    created = repository.add(make_student())

    removed = repository.delete(created.id)

    assert removed.id == created.id
    assert repository.count() == 0
    with pytest.raises(NotFoundError):
        repository.delete(created.id)


def test_get_all_sorted_by_id_and_validation() -> None:
    """get_all() сортирует по id; некорректный объект не принимается."""
    repository = StudentRepository()
    repository.add(make_student(student_id=5, name="Петров Пётр Петрович"))
    repository.add(make_student(student_id=2, name="Сидоров Семён Семёнович"))

    assert [student.id for student in repository.get_all()] == [2, 5]

    with pytest.raises(ValidationError):
        repository.add("не студент")  # type: ignore[arg-type]
