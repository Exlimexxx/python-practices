"""Модели предметной области (этапы 1-2 методички).

Вариант 4 "Университет". Основная сущность -- Student:

    id     -- идентификатор (int, 0 означает "ещё не присвоен");
    name   -- ФИО студента;
    group  -- учебная группа;
    grades -- список оценок (2..5), минимум одна;
    email  -- контактный e-mail (дополнительное поле);
    year   -- курс обучения, 1..6 (дополнительное поле);
    status -- статус обучения (дополнительное поле).

Итого: идентификатор + шесть дополнительных полей (требовалось минимум три).
Модуль не знает ничего о сети и о хранилище -- это чистые данные.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field, replace
from typing import Any, Dict, Iterable, List, Mapping

from exceptions import ValidationError

#: Минимальная и максимальная допустимая оценка.
MIN_GRADE: int = 2
MAX_GRADE: int = 5

#: Допустимые статусы студента.
ALLOWED_STATUSES: frozenset[str] = frozenset(
    {"active", "academic_leave", "expelled"}
)

#: Простая проверка формата e-mail (без внешних библиотек).
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")


def parse_grades(value: Any) -> List[int]:
    """Приводит произвольное значение к списку целых оценок 2..5.

    Принимает список чисел, список строк, строку вида "5 4 3" или "5,4,3".
    """
    if value is None:
        raise ValidationError("Поле 'grades' обязательно и не может быть пустым")
    if isinstance(value, str):
        items: Iterable[Any] = [part for part in re.split(r"[,\s;]+", value) if part]
    elif isinstance(value, (list, tuple)):
        items = value
    else:
        raise ValidationError(
            "Поле 'grades' должно быть списком оценок или строкой", "validation_error"
        )

    grades: List[int] = []
    for item in items:
        try:
            grade = int(item)
        except (TypeError, ValueError):
            raise ValidationError(f"Оценка {item!r} не является целым числом")
        if not MIN_GRADE <= grade <= MAX_GRADE:
            raise ValidationError(
                f"Оценка {grade} вне диапазона {MIN_GRADE}..{MAX_GRADE}"
            )
        grades.append(grade)

    if not grades:
        raise ValidationError("Список оценок не может быть пустым")
    return grades


def parse_int(
    value: Any,
    field_name: str,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    """Аккуратно преобразует значение в int с проверкой границ."""
    if isinstance(value, bool) or value is None:
        raise ValidationError(f"Поле '{field_name}' должно быть целым числом")
    try:
        result = int(value)
    except (TypeError, ValueError):
        raise ValidationError(f"Поле '{field_name}' должно быть целым числом")
    if minimum is not None and result < minimum:
        raise ValidationError(f"Поле '{field_name}' не может быть меньше {minimum}")
    if maximum is not None and result > maximum:
        raise ValidationError(f"Поле '{field_name}' не может быть больше {maximum}")
    return result


@dataclass
class Student:
    """Студент университета -- основная сущность варианта 4."""

    id: int
    name: str
    group: str
    grades: List[int] = field(default_factory=list)
    email: str = ""
    year: int = 1
    status: str = "active"

    # ------------------------------------------------------------------
    # вычисляемые свойства
    # ------------------------------------------------------------------
    @property
    def average(self) -> float:
        """Средний балл студента (0.0, если оценок нет)."""
        if not self.grades:
            return 0.0
        return round(sum(self.grades) / len(self.grades), 2)

    # ------------------------------------------------------------------
    # сериализация
    # ------------------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        """Словарь для JSON-протокола (плоская структура)."""
        data = asdict(self)
        data["grades"] = list(self.grades)
        data["average_grade"] = self.average
        return data

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "Student":
        """Создаёт студента из словаря запроса с полной проверкой полей."""
        if not isinstance(payload, Mapping):
            raise ValidationError("Данные студента должны быть объектом JSON")

        missing = [key for key in ("name", "group", "grades") if key not in payload]
        if missing:
            raise ValidationError(
                "Отсутствуют обязательные поля: " + ", ".join(missing)
            )

        student = cls(
            id=parse_int(payload.get("id", 0), "id", minimum=0),
            name=str(payload.get("name", "")).strip(),
            group=str(payload.get("group", "")).strip(),
            grades=parse_grades(payload.get("grades")),
            email=str(payload.get("email", "") or "").strip(),
            year=parse_int(payload.get("year", 1), "year", minimum=1, maximum=6),
            status=str(payload.get("status", "active") or "active").strip().lower(),
        )
        student.validate()
        return student

    # ------------------------------------------------------------------
    # проверка корректности
    # ------------------------------------------------------------------
    def validate(self) -> None:
        """Проверяет корректность всех полей, иначе ValidationError."""
        if not isinstance(self.id, int) or self.id < 0:
            raise ValidationError("Поле 'id' должно быть неотрицательным целым")

        if not self.name or len(self.name) < 3:
            raise ValidationError("ФИО должно содержать минимум 3 символа")

        if not self.group or len(self.group) > 20:
            raise ValidationError("Группа должна быть непустой строкой до 20 символов")

        # оценки проверяются повторно: dataclass можно собрать и вручную
        self.grades = parse_grades(self.grades)

        if self.email and not EMAIL_RE.match(self.email):
            raise ValidationError(f"Некорректный e-mail: {self.email!r}")

        if not 1 <= self.year <= 6:
            raise ValidationError("Курс обучения должен быть в диапазоне 1..6")

        if self.status not in ALLOWED_STATUSES:
            raise ValidationError(
                "Недопустимый статус "
                f"{self.status!r}; разрешены {sorted(ALLOWED_STATUSES)}"
            )

    def copy_with(self, **changes: Any) -> "Student":
        """Возвращает копию студента с изменёнными полями (без мутации)."""
        return replace(self, **changes)
