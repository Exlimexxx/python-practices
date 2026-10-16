# -*- coding: utf-8 -*-
"""Консольный HTTP-клиент REST API кинотеатра (лабораторная работа №10, вариант 4).

Клиент использует библиотеку requests и предоставляет консольное меню:
список, получение объекта, создание, PUT, PATCH, удаление, фильтрация,
сортировка, специализированная операция и проверка кода 405.

Запуск::

    python client.py
    MOVIE_API_URL=http://127.0.0.1:5010 python client.py
"""
from __future__ import annotations

import json
import os
import sys
import urllib.parse
from dataclasses import dataclass
from typing import Any, Callable

import requests

MENU = """
=========================
       REST CLIENT
=========================
1. Получить список
2. Получить объект
3. Создать
4. Изменить (PUT)
5. Частично изменить (PATCH)
6. Удалить
7. Фильтрация
8. Сортировка
9. Специализированная операция (фильмы по жанру)
10. Проверка ошибки 405 (DELETE /movies)
0. Выход
========================="""


@dataclass
class ClientConfig:
    """Настройки подключения к API."""

    base_url: str = "http://127.0.0.1:5010"
    timeout: float = 5.0


class ApiClientError(Exception):
    """Ошибка сетевого взаимодействия с API (сервер недоступен и т. п.)."""


class MovieApiClient:
    """Тонкая обёртка над requests для ресурса /movies."""

    def __init__(self, config: ClientConfig) -> None:
        self._config = config
        self._session = requests.Session()

    # --- служебные методы -------------------------------------------------
    def _url(self, path: str) -> str:
        """Собирает полный URL."""
        return self._config.base_url.rstrip("/") + path

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> requests.Response:
        """Выполняет запрос и печатает его параметры и ответ."""
        url = self._url(path)
        query = ""
        clean_params = {key: value for key, value in (params or {}).items() if value not in (None, "")}
        if clean_params:
            query = "?" + urllib.parse.urlencode(clean_params)
        print(f"\n>>> {method} {url}{query}")
        if json_body is not None:
            print("    Content-Type: application/json")
            print(f"    тело запроса: {json.dumps(json_body, ensure_ascii=False)}")
        try:
            response = self._session.request(
                method,
                url,
                params=clean_params or None,
                json=json_body,
                timeout=self._config.timeout,
            )
        except requests.RequestException as exc:
            raise ApiClientError(f"не удалось выполнить запрос ({exc})") from exc
        print(f"<<< HTTP {response.status_code} {response.reason}")
        self._print_payload(response)
        return response

    @staticmethod
    def _print_payload(response: requests.Response) -> None:
        """Печатает тело ответа (JSON или как обычный текст)."""
        if not response.content:
            print("    (тело ответа пустое)")
            return
        try:
            payload = response.json()
        except ValueError:
            print("    " + response.text.strip())
            return
        text = json.dumps(payload, ensure_ascii=False, indent=2)
        print("    " + text.replace("\n", "\n    "))

    # --- операции API -----------------------------------------------------
    def list_movies(self, **params: Any) -> requests.Response:
        """GET /movies с необязательными query-параметрами."""
        return self._request("GET", "/movies", params=params)

    def get_movie(self, movie_id: int) -> requests.Response:
        """GET /movies/{id}."""
        return self._request("GET", f"/movies/{movie_id}")

    def create_movie(self, data: dict[str, Any]) -> requests.Response:
        """POST /movies."""
        return self._request("POST", "/movies", json_body=data)

    def replace_movie(self, movie_id: int, data: dict[str, Any]) -> requests.Response:
        """PUT /movies/{id}."""
        return self._request("PUT", f"/movies/{movie_id}", json_body=data)

    def patch_movie(self, movie_id: int, data: dict[str, Any]) -> requests.Response:
        """PATCH /movies/{id}."""
        return self._request("PATCH", f"/movies/{movie_id}", json_body=data)

    def delete_movie(self, movie_id: int) -> requests.Response:
        """DELETE /movies/{id}."""
        return self._request("DELETE", f"/movies/{movie_id}")

    def delete_collection(self) -> requests.Response:
        """DELETE /movies — метод не поддерживается (демонстрация 405)."""
        return self._request("DELETE", "/movies")

    def movies_by_genre(self, genre: str) -> requests.Response:
        """GET /movies/by-genre?genre=... — специализированная операция."""
        return self._request("GET", "/movies/by-genre", params={"genre": genre})


# ---------------------------------------------------------------------------
# Вспомогательные функции ввода
# ---------------------------------------------------------------------------
def _ask(prompt: str) -> str:
    """Читает строку из stdin и печатает введённое значение."""
    value = input(prompt)
    print(f"   [введено: {value if value.strip() else '<пусто>'}]")
    return value


def _ask_number(prompt: str, cast: Callable[[str], Any]) -> Any:
    """Читает число; при ошибке возвращает исходный текст (сервер вернёт 400)."""
    raw = _ask(prompt).strip()
    if raw == "":
        return ""
    try:
        return cast(raw)
    except ValueError:
        return raw


def _read_movie_payload() -> dict[str, Any]:
    """Считывает все поля фильма (для POST и PUT)."""
    return {
        "title": _ask("Название (title): "),
        "genre": _ask("Жанр (genre): "),
        "duration": _ask_number("Длительность, мин (duration): ", int),
        "rating": _ask_number("Рейтинг 0..10 (rating): ", float),
        "price": _ask_number("Цена билета, руб. (price): ", float),
    }


def _read_patch_payload() -> dict[str, Any]:
    """Считывает только те поля, которые нужно изменить (для PATCH)."""
    print("Оставьте поле пустым, чтобы не изменять его.")
    payload: dict[str, Any] = {}

    title = _ask("Название (title): ").strip()
    if title:
        payload["title"] = title
    genre = _ask("Жанр (genre): ").strip()
    if genre:
        payload["genre"] = genre
    duration = _ask("Длительность, мин (duration): ").strip()
    if duration:
        try:
            payload["duration"] = int(duration)
        except ValueError:
            payload["duration"] = duration
    rating = _ask("Рейтинг 0..10 (rating): ").strip()
    if rating:
        try:
            payload["rating"] = float(rating)
        except ValueError:
            payload["rating"] = rating
    price = _ask("Цена билета, руб. (price): ").strip()
    if price:
        try:
            payload["price"] = float(price)
        except ValueError:
            payload["price"] = price
    return payload


def _read_id(prompt: str) -> int:
    """Считывает идентификатор фильма."""
    raw = _ask(prompt).strip()
    return int(raw)


# ---------------------------------------------------------------------------
# Консольное меню
# ---------------------------------------------------------------------------
def run_menu(client: MovieApiClient) -> None:
    """Основной цикл консольного меню."""
    print(MENU)
    while True:
        choice = _ask("Выберите действие (1-10, 0 — выход): ").strip()
        try:
            if choice == "1":
                client.list_movies()
            elif choice == "2":
                client.get_movie(_read_id("Введите id фильма: "))
            elif choice == "3":
                client.create_movie(_read_movie_payload())
            elif choice == "4":
                movie_id = _read_id("Введите id изменяемого фильма: ")
                client.replace_movie(movie_id, _read_movie_payload())
            elif choice == "5":
                movie_id = _read_id("Введите id фильма: ")
                client.patch_movie(movie_id, _read_patch_payload())
            elif choice == "6":
                client.delete_movie(_read_id("Введите id удаляемого фильма: "))
            elif choice == "7":
                genre = _ask("Жанр (genre, пусто — без фильтра): ").strip()
                min_rating = _ask("Минимальный рейтинг (min_rating, пусто — без фильтра): ").strip()
                max_price = _ask("Максимальная цена (max_price, пусто — без фильтра): ").strip()
                client.list_movies(genre=genre, min_rating=min_rating, max_price=max_price)
            elif choice == "8":
                sort = _ask("Поле сортировки (price|rating|title|duration): ").strip()
                order = _ask("Направление (asc|desc): ").strip()
                client.list_movies(sort=sort, order=order)
            elif choice == "9":
                genre = _ask("Жанр для специализированной операции: ").strip()
                client.movies_by_genre(genre)
            elif choice == "10":
                client.delete_collection()
            elif choice == "0":
                print("\nВыход из клиента.")
                return
            else:
                print("Неизвестный пункт меню, повторите ввод.")
        except ApiClientError as exc:
            print(f"\nОшибка соединения: {exc}")
        except ValueError as exc:
            print(f"\nНекорректный ввод: {exc}")


def main() -> int:
    """Точка входа клиента."""
    base_url = os.environ.get("MOVIE_API_URL", "http://127.0.0.1:5010")
    client = MovieApiClient(ClientConfig(base_url=base_url))
    print("=" * 64)
    print(" REST-клиент кинотеатра (вариант 4)")
    print(f" Базовый адрес API: {base_url}")
    print("=" * 64)
    try:
        run_menu(client)
    except (EOFError, KeyboardInterrupt):
        print("\nВвод завершён, клиент останавливается.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
