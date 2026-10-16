# -*- coding: utf-8 -*-
"""Тесты REST API через app.test_client() (5+ тестов по требованиям методички)."""
from __future__ import annotations

from flask.testing import FlaskClient

NEW_MOVIE = {
    "title": "Дюна",
    "genre": "фантастика",
    "duration": 155,
    "rating": 8.3,
    "price": 600.0,
}


def test_get_movies_returns_200_and_json_list(client: FlaskClient) -> None:
    """GET /movies — список фильмов и корректный Content-Type."""
    response = client.get("/movies")

    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("application/json")
    payload = response.get_json()
    assert isinstance(payload, list)
    assert len(payload) == 6
    assert payload[0]["title"] == "Интерстеллар"


def test_get_movies_filtering_and_sorting(client: FlaskClient) -> None:
    """Фильтрация по query-параметрам и сортировка."""
    response = client.get("/movies?genre=фантастика&min_rating=8.7")
    assert response.status_code == 200
    assert [movie["title"] for movie in response.get_json()] == ["Начало"]

    response = client.get("/movies?max_price=450&sort=price&order=desc")
    prices = [movie["price"] for movie in response.get_json()]
    assert prices == sorted(prices, reverse=True)
    assert all(price <= 450 for price in prices)

    assert client.get("/movies?sort=unknown").status_code == 400
    assert client.get("/movies?min_rating=abc").status_code == 400


def test_get_movie_200_and_404(client: FlaskClient) -> None:
    """GET /movies/{id} — успех и отсутствующий объект."""
    response = client.get("/movies/1")
    assert response.status_code == 200
    assert response.get_json()["title"] == "Интерстеллар"

    missing = client.get("/movies/999")
    assert missing.status_code == 404
    assert missing.get_json() == {"error": "Фильм с id=999 не найден", "code": "MOVIE_NOT_FOUND"}


def test_get_movie_with_invalid_id_returns_400(client: FlaskClient) -> None:
    """Некорректный path-параметр даёт 400 Bad Request."""
    response = client.get("/movies/abc")

    assert response.status_code == 400
    assert response.get_json()["code"] == "INVALID_ID"


def test_post_creates_201_and_rejects_invalid_400(client: FlaskClient) -> None:
    """POST /movies — создание и отказ при некорректных данных."""
    response = client.post("/movies", json=NEW_MOVIE)

    assert response.status_code == 201
    created = response.get_json()
    assert created["id"] == 7
    assert created["title"] == "Дюна"
    assert response.headers["Location"].endswith("/movies/7")

    invalid = client.post(
        "/movies",
        json={"title": " ", "genre": "фантастика", "duration": -5, "rating": 11, "price": 0},
    )
    assert invalid.status_code == 400
    assert invalid.get_json()["code"] == "VALIDATION_ERROR"

    assert len(client.get("/movies").get_json()) == 7  # некорректный объект не создан


def test_post_with_broken_json_returns_400(client: FlaskClient) -> None:
    """Некорректный JSON в теле запроса даёт 400."""
    response = client.post("/movies", data="{not a json", content_type="application/json")

    assert response.status_code == 400
    assert response.get_json()["code"] == "VALIDATION_ERROR"


def test_put_replaces_movie(client: FlaskClient) -> None:
    """PUT /movies/{id} — полное изменение (200) и 404 для отсутствующего."""
    payload = {
        "title": "Интерстеллар (режиссёрская версия)",
        "genre": "фантастика",
        "duration": 180,
        "rating": 9.0,
        "price": 700.0,
    }
    response = client.put("/movies/1", json=payload)

    assert response.status_code == 200
    assert response.get_json()["title"] == payload["title"]
    assert response.get_json()["duration"] == 180
    assert client.put("/movies/999", json=payload).status_code == 404


def test_patch_changes_only_given_fields(client: FlaskClient) -> None:
    """PATCH /movies/{id} — частичное изменение."""
    response = client.patch("/movies/1", json={"price": 999.0})

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["price"] == 999.0
    assert payload["title"] == "Интерстеллар"
    assert client.patch("/movies/1", json={}).status_code == 400


def test_delete_returns_204_and_then_404(client: FlaskClient) -> None:
    """DELETE /movies/{id} — 204 No Content, повторное удаление даёт 404."""
    response = client.delete("/movies/2")

    assert response.status_code == 204
    assert response.get_data(as_text=True) == ""
    assert client.get("/movies/2").status_code == 404
    assert client.delete("/movies/2").status_code == 404


def test_by_genre_specialized_endpoint(client: FlaskClient) -> None:
    """Специализированный endpoint GET /movies/by-genre."""
    response = client.get("/movies/by-genre?genre=фантастика")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["genre"] == "фантастика"
    assert payload["count"] == 2
    assert [movie["title"] for movie in payload["movies"]] == ["Начало", "Интерстеллар"]

    assert client.get("/movies/by-genre").status_code == 400
    assert client.get("/movies/by-genre?genre=вестерн").get_json()["count"] == 0


def test_method_not_allowed_405(client: FlaskClient) -> None:
    """DELETE /movies — метод не поддерживается коллекцией."""
    response = client.delete("/movies")

    assert response.status_code == 405
    assert response.get_json()["code"] == "METHOD_NOT_ALLOWED"
    assert client.put("/movies", json=NEW_MOVIE).status_code == 405


def test_unknown_route_returns_404(client: FlaskClient) -> None:
    """Несуществующий маршрут — 404 в едином формате."""
    response = client.get("/unknown")

    assert response.status_code == 404
    assert response.get_json()["code"] == "NOT_FOUND"
