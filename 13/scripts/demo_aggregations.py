"""Демонстрация aggregation pipeline MongoDB (2+ агрегации)."""
from __future__ import annotations

from common import make_service, print_backends, setup_logging, title

setup_logging()


def show_rows(title_text: str, rows: list[dict], fields: tuple[str, ...]) -> None:
    print("\n--- " + title_text)
    for row in rows:
        print("    " + " | ".join(f"{f}={row.get(f)}" for f in fields))


def main() -> None:
    service, info = make_service(reset=True)
    repo = service.repository

    title("3. АГРЕГАЦИИ MONGODB (aggregation pipeline)")
    print_backends(info)

    # Агрегация 1: количество фильмов и средний рейтинг по жанрам
    by_genre = repo.aggregate(
        [
            {"$unwind": "$genres"},
            {"$group": {"_id": "$genres", "count": {"$sum": 1}, "avg_rating": {"$avg": "$rating"}, "max_rating": {"$max": "$rating"}}},
            {"$sort": {"count": -1, "avg_rating": -1}},
        ]
    )
    show_rows("Агрегация 1: $unwind genres + $group -> фильмов и средний рейтинг по жанрам", by_genre, ("_id", "count", "avg_rating", "max_rating"))

    # Агрегация 2: топ режиссёров по числу фильмов и среднему рейтингу
    by_director = repo.aggregate(
        [
            {"$match": {"status": {"$ne": "archived"}}},
            {"$group": {"_id": "$director.name", "films": {"$sum": 1}, "avg_rating": {"$avg": "$rating"}}},
            {"$sort": {"films": -1, "avg_rating": -1}},
            {"$limit": 5},
        ]
    )
    show_rows("Агрегация 2: $match + $group по director.name + $sort + $limit", by_director, ("_id", "films", "avg_rating"))

    # Агрегация 3: распределение по статусам
    by_status = repo.aggregate(
        [
            {"$group": {"_id": "$status", "count": {"$sum": 1}, "avg_rating": {"$avg": "$rating"}}},
            {"$sort": {"count": -1}},
        ]
    )
    show_rows("Агрегация 3: количество фильмов по статусу", by_status, ("_id", "count", "avg_rating"))

    # Агрегация 4: топ-5 по рейтингу с проекцией
    top = repo.aggregate(
        [
            {"$sort": {"rating": -1}},
            {"$limit": 5},
            {"$project": {"_id": 0, "title": 1, "rating": 1, "year": 1, "director": "$director.name"}},
        ]
    )
    show_rows("Агрегация 4: топ-5 фильмов по рейтингу ($project)", top, ("title", "rating", "year", "director"))

    # Агрегация 5: средний рейтинг по десятилетиям
    by_decade = repo.aggregate(
        [
            {"$group": {"_id": {"$multiply": [{"$floor": {"$divide": ["$year", 10]}}, 10]}, "count": {"$sum": 1}, "avg_rating": {"$avg": "$rating"}}},
            {"$sort": {"_id": 1}},
        ]
    )
    show_rows("Агрегация 5: фильмы по десятилетиям", by_decade, ("_id", "count", "avg_rating"))

    # Агрегация 6: общее число документов в конвейере
    total = repo.aggregate([{"$count": "total"}])
    show_rows("Агрегация 6: $count -> всего документов", total, ("total",))

    # Агрегация 7: статистика, собранная сервисом
    stats = service.statistics()
    print("\n--- Сводная статистика сервиса (через агрегацию):")
    print(f"    всего фильмов      : {stats['total']}")
    print(f"    средний рейтинг    : {stats['avg_rating']}")
    print(f"    максимальный рейтинг: {stats['max_rating']}")
    print(f"    по статусам        : {stats['by_status']}")


if __name__ == "__main__":
    main()
