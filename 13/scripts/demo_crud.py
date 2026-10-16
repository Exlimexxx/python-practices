"""Демонстрация CRUD MongoDB (create/read/update/delete + ошибки)."""
from __future__ import annotations

from common import make_service, print_backends, setup_logging, show_json, title

from app.errors import InvalidIdentifierError, NotFoundError, ValidationError
from app.models import Director, Movie, Session

setup_logging()


def main() -> None:
    service, info = make_service(reset=True)
    repo = service.repository

    title("1. CRUD MONGODB (коллекция cinema.movie)")
    print_backends(info)

    # ------------------------------------------------------------------ CREATE
    title("CREATE: добавление нового фильма")
    new_movie = Movie(
        title="Тестовый блокбастер",
        director=Director(name="Иван Режиссёров", country="Россия"),
        year=2024,
        genres=["боевик", "фантастика"],
        actors=["Актёр Первый", "Актёр Второй"],
        duration=123,
        rating=7.4,
        poster="https://posters.local/cinema/test.jpg",
        sessions=[Session(date="2024-06-10", time="20:00", hall="IMAX", price=500.0, format="IMAX")],
        status="coming_soon",
    )
    created_id = service.add_movie(new_movie)
    print("inserted_id =", created_id)
    show_json(repo.get_document(created_id))

    # -------------------------------------------------------------------- READ
    title("READ: получение одного документа по _id")
    loaded = service.get_movie(created_id, use_cache=False)
    print(loaded.summary())

    title("READ: список документов (sort по рейтингу, limit 5, проекция)")
    for doc in repo.find({}, projection={"title": 1, "year": 1, "rating": 1}, sort=[("rating", -1)], limit=5):
        print(" -", doc)

    title("READ: документы по условию (status = archived)")
    for doc in repo.find({"status": "archived"}, projection={"title": 1, "year": 1}, sort=[("year", 1)]):
        print(" -", doc["title"], doc["year"])

    # ------------------------------------------------------------------ UPDATE
    title("UPDATE: изменение рейтинга и статуса через $set")
    print("до  :", repo.get_document(created_id)["rating"], repo.get_document(created_id)["status"])
    updated = service.update_movie(created_id, {"rating": 8.1, "status": "showing"})
    print("после:", updated.rating, updated.status)

    title("UPDATE: добавление актёра в массив через $push")
    repo.collection.update_one({"_id": created_id}, {"$push": {"actors": "Актёр Третий"}})
    print("actors =", repo.get_document(created_id)["actors"])

    title("UPDATE: инкремент числового поля через $inc (просмотры)")
    repo.collection.update_one({"_id": created_id}, {"$inc": {"views": 1}})
    print("views =", repo.get_document(created_id).get("views"))

    # ------------------------------------------------------------------ DELETE
    title("DELETE: удаление документа")
    before = repo.count({})
    service.delete_movie(created_id)
    after = repo.count({})
    print(f"документов до удаления: {before}, после: {after}")
    print("повторный поиск удалённого:", repo.find_one({"_id": created_id}))

    # --------------------------------------------------------- ОБРАБОТКА ОШИБОК
    title("ОБРАБОТКА ОШИБОК")
    scenarios = []

    try:
        service.get_movie("")
    except InvalidIdentifierError as exc:
        scenarios.append(("пустой идентификатор", f"InvalidIdentifierError: {exc}"))

    try:
        service.get_movie("ffffffffffffffffffffffff")
    except NotFoundError as exc:
        scenarios.append(("несуществующий _id", f"NotFoundError: {exc}"))

    try:
        bad = Movie(
            title="Некорректный фильм",
            director=Director(name="Режиссёр", country="США"),
            year=2024,
            genres=["драма"],
            actors=[],
            duration=0,
            rating=15.0,
            status="showing",
        )
        service.add_movie(bad)
    except ValidationError as exc:
        scenarios.append(("некорректные данные (рейтинг 15)", f"ValidationError: {exc}"))

    for name, message in scenarios:
        print(f" * {name}: {message}")

    print("\nПрограмма не завершилась аварийно: все ошибки обработаны.")


if __name__ == "__main__":
    main()
