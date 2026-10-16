"""Демонстрация запросов MongoDB (>= 10 различных запросов)."""
from __future__ import annotations

from common import make_service, print_backends, setup_logging, title

setup_logging()

QUERY_TOTAL = 0


def show(query: str, docs: list[dict], fields: tuple[str, ...] = ("title", "year", "rating")) -> None:
    """Печать результата запроса в компактном виде."""
    global QUERY_TOTAL
    QUERY_TOTAL += 1
    print(f"\n--- Запрос {QUERY_TOTAL}: {query}")
    print(f"    найдено документов: {len(docs)}")
    for doc in docs[:8]:
        parts = []
        for field in fields:
            value = doc.get(field)
            parts.append(f"{field}={value}")
        print("    * " + ", ".join(parts))
    if len(docs) > 8:
        print(f"    ... ещё {len(docs) - 8}")


def main() -> None:
    service, info = make_service(reset=True)
    repo = service.repository

    title("2. ЗАПРОСЫ MONGODB К КОЛЛЕКЦИИ cinema.movie")
    print_backends(info)

    # 1-3: фильтрация
    docs = repo.find({"genres": "фантастика"}, projection={"title": 1, "rating": 1, "genres": 1}, sort=[("rating", -1)])
    show("фильтр по элементу массива genres = 'фантастика'", docs, ("title", "rating"))

    docs = repo.find({"rating": {"$gte": 8.5}}, projection={"title": 1, "rating": 1}, sort=[("rating", -1)])
    show("фильтр по числовому полю rating >= 8.5", docs, ("title", "rating"))

    docs = repo.find({"status": "archived"}, projection={"title": 1, "year": 1, "status": 1}, sort=[("year", 1)])
    show("фильтр по полю-категории status = 'archived'", docs, ("title", "year"))

    # 4-5: сортировки
    docs = repo.find({}, projection={"title": 1, "year": 1}, sort=[("year", -1)], limit=5)
    show("сортировка по году (убывание), limit 5", docs, ("title", "year"))

    docs = repo.find({}, projection={"title": 1, "rating": 1, "year": 1}, sort=[("rating", -1), ("year", 1)], limit=5)
    show("сортировка по рейтингу (убывание) и году (возрастание)", docs, ("title", "rating", "year"))

    # 6: ограничение количества
    docs = repo.find({}, projection={"title": 1, "duration": 1}, sort=[("duration", -1)], limit=3)
    show("три самых длинных фильма (sort duration + limit 3)", docs, ("title", "duration"))

    # 7: несколько условий
    docs = repo.find(
        {"$and": [{"genres": "драма"}, {"rating": {"$gte": 8.8}}, {"year": {"$lt": 2010}}]},
        projection={"title": 1, "rating": 1, "year": 1},
        sort=[("rating", -1)],
    )
    show("несколько условий: жанр драма И рейтинг >= 8.8 И год < 2010", docs, ("title", "rating", "year"))

    # 8: вложенное поле
    docs = repo.find({"director.name": "Кристофер Нолан"}, projection={"title": 1, "year": 1, "director": 1}, sort=[("year", 1)])
    show("поиск по вложенному полю director.name = 'Кристофер Нолан'", docs, ("title", "year"))

    # 9: вложенное поле + диапазон
    docs = repo.find(
        {"$and": [{"director.country": "США"}, {"rating": {"$gt": 8.7}}]},
        projection={"title": 1, "rating": 1, "director.country": 1},
        sort=[("rating", -1)],
    )
    show("вложенное поле director.country = 'США' и rating > 8.7", docs, ("title", "rating"))

    # 10: элемент массива actors
    docs = repo.find({"actors": "Леонардо ДиКаприо"}, projection={"title": 1, "actors": 1}, sort=[("year", 1)])
    show("поиск по элементу массива actors = 'Леонардо ДиКаприо'", docs, ("title",))

    # 11: $all по массиву
    docs = repo.find({"genres": {"$all": ["драма", "криминал"]}}, projection={"title": 1, "genres": 1})
    show("массив содержит все элементы ($all: драма + криминал)", docs, ("title", "genres"))

    # 12: вложенный массив sessions
    docs = repo.find({"sessions.hall": "IMAX"}, projection={"title": 1, "sessions": 1}, sort=[("title", 1)], limit=4)
    show("запрос по вложенному массиву sessions.hall = 'IMAX'", docs, ("title",))

    # 13: regex по названию
    docs = repo.find({"title": {"$regex": "^Властелин"}}, projection={"title": 1, "year": 1}, sort=[("year", 1)])
    show("regex по названию: ^Властелин", docs, ("title", "year"))

    # 14: $in по статусам
    docs = repo.find({"status": {"$in": ["coming_soon"]}}, projection={"title": 1, "status": 1}, sort=[("title", 1)])
    show("статус входит в список ($in: coming_soon)", docs, ("title", "status"))

    # 15: проекция только нужных полей
    docs = repo.find({"rating": {"$gte": 9.0}}, projection={"title": 1, "rating": 1, "_id": 0}, sort=[("rating", -1)])
    show("проекция без _id: только title и rating (rating >= 9.0)", docs, ("title", "rating"))

    # 16: distinct
    genres = sorted(repo.distinct("genres"))
    print(f"\n--- Запрос {16}: distinct('genres') -> {len(genres)} уникальных жанров")
    print("    " + ", ".join(genres))

    # 17: count по условию
    count = repo.count({"sessions.price": {"$gte": 400}})
    print(f"\n--- Запрос 17: count документов с сеансом дороже 400 руб. = {count}")

    print(f"\nИТОГО выполнено различных запросов: {QUERY_TOTAL + 2}")


if __name__ == "__main__":
    main()
