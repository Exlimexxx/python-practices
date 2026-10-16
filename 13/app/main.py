"""Точка входа приложения «Кинотеатр — фильмы» (лабораторная работа №13).

Приложение подключается к MongoDB и Redis; при их недоступности автоматически
переключается на встроенные in-memory реализации и продолжает работу.

Запуск:
    python -m app.main            # интерактивное меню
Настройка через переменные окружения:
    MONGO_URI, MONGO_DB, REDIS_URL, CACHE_TTL
"""
from __future__ import annotations

import logging
import os
import sys
from typing import Any

from .cache import RedisCache
from .errors import CinemaError
from .models import Director, Movie, Session
from .mongodb import connect_mongo
from .redis_client import connect_redis
from .repository import MongoRepository
from .seed import build_movies, seed
from .service import MovieService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("cinema")

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://127.0.0.1:27017")
MONGO_DB = os.environ.get("MONGO_DB", "cinema")
REDIS_URL = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")
CACHE_TTL = int(os.environ.get("CACHE_TTL", "60"))


def build_app(ttl: int = CACHE_TTL, with_seed: bool = True) -> tuple[MovieService, dict[str, Any]]:
    """Собрать приложение: подключения, репозиторий, кэш, сервис, данные."""
    database, mongo_mode, mongo_error = connect_mongo(MONGO_URI, MONGO_DB)
    repository = MongoRepository(database["movie"])
    repository.ensure_indexes()

    client, redis_mode, redis_error = connect_redis(REDIS_URL)
    cache = RedisCache(client, namespace="cinema")
    service = MovieService(repository, cache, ttl=ttl)

    seeded = 0
    if with_seed:
        seeded = seed(build_movies(), repository)

    info = {
        "mongo_mode": mongo_mode,
        "mongo_error": mongo_error,
        "redis_mode": redis_mode,
        "redis_error": redis_error,
        "documents": repository.count({}),
        "seeded": seeded,
    }
    return service, info


def print_info(info: dict[str, Any]) -> None:
    print("=" * 70)
    print("Лабораторная работа №13. Кинотеатр — фильмы (вариант 4)")
    print("=" * 70)
    if info["mongo_mode"] == "mongodb":
        print("MongoDB : подключено (mongodb://127.0.0.1:27017, БД cinema)")
    else:
        print("MongoDB : сервер недоступен, используется in-memory реализация")
        print(f"          причина: {info['mongo_error']}")
    if info["redis_mode"] == "redis":
        print("Redis   : подключено (redis://127.0.0.1:6379/0)")
    else:
        print("Redis   : сервер недоступен, используется in-memory реализация")
        print(f"          причина: {info['redis_error']}")
    print(f"Документов в коллекции movie: {info['documents']} (добавлено при старте: {info['seeded']})")
    print("=" * 70)


def read_movie_from_input() -> Movie:
    """Считать данные фильма с клавиатуры (простая форма)."""
    title = input("Название: ").strip()
    director = input("Режиссёр: ").strip()
    country = input("Страна режиссёра: ").strip() or "—"
    year = int(input("Год: ").strip())
    genres = [g.strip() for g in input("Жанры (через запятую): ").split(",") if g.strip()]
    actors = [a.strip() for a in input("Актёры (через запятую): ").split(",") if a.strip()]
    duration = int(input("Продолжительность, мин: ").strip())
    rating = float(input("Рейтинг 0..10: ").strip())
    status = input("Статус (showing/coming_soon/archived) [showing]: ").strip() or "showing"
    return Movie(
        title=title,
        director=Director(name=director, country=country),
        year=year,
        genres=genres,
        actors=actors,
        duration=duration,
        rating=rating,
        poster="https://posters.local/cinema/new.jpg",
        sessions=[Session(date="2024-06-05", time="19:00", hall="Зал 1", price=400.0, format="2D")],
        status=status,
    )


def menu() -> None:  # pragma: no cover - интерактивный режим
    """Интерактивное меню (10 пунктов по требованию методички)."""
    service, info = build_app()
    print_info(info)
    while True:
        print("\n===== MENU =====")
        print("1. Add")
        print("2. Find")
        print("3. List")
        print("4. Search")
        print("5. Update")
        print("6. Delete")
        print("7. Statistics")
        print("8. Cache status")
        print("9. Clear cache")
        print("10. Benchmark")
        print("0. Exit")
        choice = input("Выбор: ").strip()
        try:
            if choice == "1":
                new_id = service.add_movie(read_movie_from_input())
                print(f"Добавлен фильм _id={new_id}")
            elif choice == "2":
                movie_id = input("_id фильма: ").strip()
                print(service.get_movie(movie_id).summary())
            elif choice == "3":
                for movie in service.list_movies(limit=10, sort=[("rating", -1)]):
                    print(" -", movie.summary())
            elif choice == "4":
                genre = input("Жанр: ").strip()
                for doc in service.search({"genres": genre}, sort=[("rating", -1)]):
                    print(f" - {doc['title']} ({doc['year']}) рейтинг {doc['rating']}")
            elif choice == "5":
                movie_id = input("_id фильма: ").strip()
                rating = float(input("Новый рейтинг: ").strip())
                print(service.update_movie(movie_id, {"rating": rating}).summary())
            elif choice == "6":
                movie_id = input("_id фильма: ").strip()
                print("Удалено" if service.delete_movie(movie_id) else "Не найдено")
            elif choice == "7":
                for key, value in service.statistics().items():
                    print(f" {key}: {value}")
            elif choice == "8":
                for key, value in service.cache_status().items():
                    print(f" {key}: {value if key != 'entries' else str(value)[:300]}")
            elif choice == "9":
                print(f"Удалено ключей: {service.clear_cache()}")
            elif choice == "10":
                for row in service.benchmark():
                    print(" ", row)
            elif choice == "0":
                print("Выход.")
                return
            else:
                print("Неизвестный пункт меню.")
        except CinemaError as exc:
            print(f"Ошибка: {exc}")
        except ValueError as exc:
            print(f"Некорректный ввод: {exc}")


if __name__ == "__main__":  # pragma: no cover
    try:
        menu()
    except KeyboardInterrupt:
        sys.exit(0)
