# -*- coding: utf-8 -*-
"""Схемы и валидация данных REST API кинотеатра.

Модуль отвечает за:
* сериализацию модели в JSON;
* проверку тела запроса (POST / PUT / PATCH);
* разбор query-параметров и path-параметров.

При некорректных данных поднимается ValidationError, которое HTTP-слой
преобразует в ответ 400 Bad Request с единым форматом ошибки.
"""
from __future__ import annotations

from typing import Any, Callable, Iterable

from exceptions import InvalidIdentifierError, ValidationError
from models import Movie

#: Поля, которые обязан передать клиент (id назначает сервер).
REQUIRED_FIELDS: tuple[str, ...] = ("title", "genre", "duration", "rating", "price")
#: Все поля ресурса Movie.
ALL_FIELDS: tuple[str, ...] = REQUIRED_FIELDS
#: Поля, доступные для сортировки (методичка требует минимум два).
SORT_FIELDS: tuple[str, ...] = ("price", "rating", "title", "duration")
#: Допустимые направления сортировки.
ORDER_VALUES: tuple[str, ...] = ("asc", "desc")


def movie_to_dict(movie: Movie) -> dict[str, Any]:
    """Сериализует модель в JSON-совместимый словарь."""
    return movie.to_dict()


def movies_to_list(movies: Iterable[Movie]) -> list[dict[str, Any]]:
    """Сериализует коллекцию фильмов."""
    return [movie.to_dict() for movie in movies]


def _is_number(value: Any) -> bool:
    """True для int/float, но не для bool (bool — подкласс int)."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _check_title(value: Any, errors: list[str]) -> str | None:
    """title — непустая строка длиной до 200 символов."""
    if not isinstance(value, str) or not value.strip():
        errors.append("поле 'title' должно быть непустой строкой")
        return None
    title = value.strip()
    if len(title) > 200:
        errors.append("длина поля 'title' не должна превышать 200 символов")
        return None
    return title


def _check_genre(value: Any, errors: list[str]) -> str | None:
    """genre — непустая строка."""
    if not isinstance(value, str) or not value.strip():
        errors.append("поле 'genre' должно быть непустой строкой")
        return None
    return value.strip()


def _check_duration(value: Any, errors: list[str]) -> int | None:
    """duration — целое число минут больше нуля."""
    if not _is_number(value):
        errors.append("поле 'duration' должно быть числом (минуты)")
        return None
    if isinstance(value, float) and not value.is_integer():
        errors.append("поле 'duration' должно быть целым числом минут")
        return None
    duration = int(value)
    if duration <= 0:
        errors.append("поле 'duration' должно быть больше 0")
        return None
    if duration > 600:
        errors.append("поле 'duration' не должно превышать 600 минут")
        return None
    return duration


def _check_rating(value: Any, errors: list[str]) -> float | None:
    """rating — число в диапазоне от 0 до 10."""
    if not _is_number(value):
        errors.append("поле 'rating' должно быть числом от 0 до 10")
        return None
    rating = float(value)
    if not 0.0 <= rating <= 10.0:
        errors.append("поле 'rating' должно находиться в диапазоне от 0 до 10")
        return None
    return rating


def _check_price(value: Any, errors: list[str]) -> float | None:
    """price — число больше нуля."""
    if not _is_number(value):
        errors.append("поле 'price' должно быть числом")
        return None
    price = float(value)
    if price <= 0:
        errors.append("поле 'price' должно быть больше 0")
        return None
    return price


_CHECKS: dict[str, Callable[[Any, list[str]], Any]] = {
    "title": _check_title,
    "genre": _check_genre,
    "duration": _check_duration,
    "rating": _check_rating,
    "price": _check_price,
}


def validate_movie_payload(data: Any, *, partial: bool = False) -> dict[str, Any]:
    """Проверяет тело запроса и возвращает очищенные (приведённые к типам) данные.

    :param data: разобранный JSON-объект
    :param partial: True для PATCH — достаточно одного поля
    :raises ValidationError: если данные некорректны (HTTP 400)
    """
    if not isinstance(data, dict):
        raise ValidationError("Тело запроса должно быть JSON-объектом")
    if not data:
        raise ValidationError("Тело запроса не должно быть пустым")

    unknown = sorted(set(data) - set(ALL_FIELDS))
    if unknown:
        raise ValidationError("Неизвестные поля: " + ", ".join(unknown))

    if partial:
        if not any(field in data for field in ALL_FIELDS):
            raise ValidationError("Не передано ни одного поля для изменения")
    else:
        missing = [field for field in REQUIRED_FIELDS if field not in data]
        if missing:
            raise ValidationError("Отсутствуют обязательные поля: " + ", ".join(missing))

    errors: list[str] = []
    result: dict[str, Any] = {}
    for field, check in _CHECKS.items():
        if field in data:
            value = check(data[field], errors)
            if value is not None:
                result[field] = value

    if errors:
        raise ValidationError("Некорректные данные: " + "; ".join(errors))
    return result


def parse_movie_id(raw: Any) -> int:
    """Преобразует path-параметр в int, иначе 400 Bad Request.

    :raises InvalidIdentifierError: если идентификатор не является целым числом > 0
    """
    try:
        movie_id = int(str(raw).strip())
    except (TypeError, ValueError):
        raise InvalidIdentifierError(f"Идентификатор '{raw}' не является целым числом") from None
    if movie_id <= 0:
        raise InvalidIdentifierError("Идентификатор должен быть положительным целым числом")
    return movie_id


def parse_optional_float(raw: Any, field_name: str) -> float | None:
    """Разбирает необязательный числовой query-параметр.

    :raises ValidationError: если параметр не является числом
    """
    if raw is None or str(raw).strip() == "":
        return None
    try:
        return float(str(raw).replace(",", "."))
    except ValueError:
        raise ValidationError(f"Параметр '{field_name}' должен быть числом") from None


def parse_optional_str(raw: Any) -> str | None:
    """Разбирает необязательный строковый query-параметр (пустое значение → None)."""
    if raw is None or str(raw).strip() == "":
        return None
    return str(raw).strip()


def parse_sort_field(raw: Any) -> str | None:
    """Проверяет поле сортировки.

    :raises ValidationError: если поле не входит в SORT_FIELDS
    """
    value = parse_optional_str(raw)
    if value is None:
        return None
    value = value.lower()
    if value not in SORT_FIELDS:
        raise ValidationError("Параметр 'sort' должен принимать значения: " + ", ".join(SORT_FIELDS))
    return value


def parse_order(raw: Any) -> str:
    """Проверяет направление сортировки (по умолчанию asc).

    :raises ValidationError: если направление не asc и не desc
    """
    value = parse_optional_str(raw)
    if value is None:
        return "asc"
    value = value.lower()
    if value not in ORDER_VALUES:
        raise ValidationError("Параметр 'order' должен принимать значения: " + ", ".join(ORDER_VALUES))
    return value
