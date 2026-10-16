"""Автотесты REST API (pytest + FastAPI TestClient).

Покрывают все обязательные сценарии п. 37 методички:
список, получение, 404, создание, валидацию, PUT, PATCH, DELETE,
фильтрацию, сортировку, пагинацию, поиск, статистику и кэш.
"""
from __future__ import annotations

from app.cache import get_cache

# --------------------------------------------------------------- служебные


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["resource"] == "/movies"
    assert body["variant"] == 4


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_openapi_schema_contains_endpoints(client):
    schema = client.get("/openapi.json").json()
    paths = schema["paths"]
    assert "/movies" in paths
    assert "/movies/{movie_id}" in paths
    assert "/movies/search" in paths
    assert "/movies/stats" in paths
    assert "/movies/by-genre" in paths
    assert {"get", "post"} <= set(paths["/movies"].keys())
    assert {"get", "put", "patch", "delete"} <= set(paths["/movies/{movie_id}"].keys())


# ----------------------------------------------------------------- create


def test_create_movie_returns_201(client, sample_movie):
    response = client.post("/movies", json=sample_movie)
    assert response.status_code == 201
    body = response.json()
    assert body["id"] > 0
    assert body["title"] == sample_movie["title"]
    assert body["rating"] == sample_movie["rating"]


def test_create_movie_validation_error_422(client, sample_movie):
    bad = {**sample_movie, "rating": 99}
    response = client.post("/movies", json=bad)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_create_movie_missing_field_422(client, sample_movie):
    sample_movie.pop("title")
    response = client.post("/movies", json=sample_movie)
    assert response.status_code == 422


def test_create_movie_invalid_year_422(client, sample_movie):
    bad = {**sample_movie, "year": 1200}
    response = client.post("/movies", json=bad)
    assert response.status_code == 422


# ------------------------------------------------------------------- read


def test_list_empty(client):
    response = client.get("/movies")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 0
    assert body["items"] == []


def test_list_returns_created_movies(client, sample_movie):
    client.post("/movies", json=sample_movie)
    client.post("/movies", json={**sample_movie, "title": "Интерстеллар", "genre": "драма"})
    body = client.get("/movies").json()
    assert body["total"] == 2
    assert len(body["items"]) == 2


def test_get_existing_movie(client, created_movie):
    response = client.get(f"/movies/{created_movie['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created_movie["id"]


def test_get_missing_movie_404(client):
    response = client.get("/movies/9999")
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "movie_not_found"


# --------------------------------------------------------------- pagination


def test_pagination(client, sample_movie):
    for i in range(5):
        client.post("/movies", json={**sample_movie, "title": f"Фильм {i}", "rating": 5.0 + i})
    page = client.get("/movies?limit=2&offset=1").json()
    assert page["limit"] == 2
    assert page["offset"] == 1
    assert page["total"] == 5
    assert len(page["items"]) == 2


# --------------------------------------------------------------- filtering


def test_filter_by_genre(client, sample_movie):
    client.post("/movies", json=sample_movie)
    client.post("/movies", json={**sample_movie, "title": "Драма", "genre": "драма"})
    body = client.get("/movies?genre=драма").json()
    assert body["total"] == 1
    assert body["items"][0]["genre"] == "драма"


def test_filter_by_min_rating(client, sample_movie):
    client.post("/movies", json={**sample_movie, "title": "A", "rating": 9.5})
    client.post("/movies", json={**sample_movie, "title": "B", "rating": 6.0})
    body = client.get("/movies?min_rating=8").json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "A"


def test_filter_by_year(client, sample_movie):
    client.post("/movies", json={**sample_movie, "title": "A", "year": 1999})
    client.post("/movies", json={**sample_movie, "title": "B", "year": 2010})
    body = client.get("/movies?year=1999").json()
    assert body["total"] == 1
    assert body["items"][0]["year"] == 1999


# ----------------------------------------------------------------- sorting


def test_sort_asc_and_desc(client, sample_movie):
    client.post("/movies", json={**sample_movie, "title": "Low", "rating": 3.0})
    client.post("/movies", json={**sample_movie, "title": "High", "rating": 9.9})
    asc = client.get("/movies?sort=rating&order=asc").json()["items"]
    desc = client.get("/movies?sort=rating&order=desc").json()["items"]
    assert asc[0]["title"] == "Low"
    assert desc[0]["title"] == "High"


def test_invalid_sort_returns_400(client):
    response = client.get("/movies?sort=hacker")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_query"


def test_invalid_order_returns_400(client):
    response = client.get("/movies?order=sideways")
    assert response.status_code == 400


# ------------------------------------------------------------------ search


def test_search_finds_by_title(client, sample_movie):
    client.post("/movies", json=sample_movie)
    client.post("/movies", json={**sample_movie, "title": "Матрица", "director": "Вачовски"})
    body = client.get("/movies/search?q=матрица").json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "Матрица"


def test_by_genre_endpoint(client, sample_movie):
    client.post("/movies", json={**sample_movie, "genre": "боевик"})
    client.post("/movies", json={**sample_movie, "title": "Комедия", "genre": "комедия"})
    body = client.get("/movies/by-genre?genre=боевик").json()
    assert body["total"] == 1


def test_search_empty_query_is_400_or_422(client):
    response = client.get("/movies/search?q=")
    assert response.status_code in (400, 422)


# ------------------------------------------------------------------- stats


def test_stats(client, sample_movie):
    client.post("/movies", json={**sample_movie, "rating": 8.0, "duration": 100})
    client.post("/movies", json={**sample_movie, "title": "B", "rating": 6.0, "duration": 120, "genre": "драма"})
    body = client.get("/movies/stats").json()
    assert body["total"] == 2
    assert body["average_rating"] == 7.0
    assert body["max_rating"] == 8.0
    assert body["min_rating"] == 6.0
    assert body["total_duration"] == 220
    assert len(body["by_genre"]) == 2


def test_stats_empty_database(client):
    body = client.get("/movies/stats").json()
    assert body["total"] == 0
    assert body["average_rating"] is None


# --------------------------------------------------------------- update/del


def test_put_replaces_movie(client, created_movie, sample_movie):
    new_data = {**sample_movie, "title": "Начало (ремастер)", "rating": 9.0}
    response = client.put(f"/movies/{created_movie['id']}", json=new_data)
    assert response.status_code == 200
    assert response.json()["title"] == "Начало (ремастер)"
    assert response.json()["rating"] == 9.0


def test_patch_updates_only_passed_fields(client, created_movie):
    response = client.patch(f"/movies/{created_movie['id']}", json={"rating": 7.7})
    assert response.status_code == 200
    body = response.json()
    assert body["rating"] == 7.7
    assert body["title"] == created_movie["title"]


def test_patch_missing_movie_404(client):
    response = client.patch("/movies/4242", json={"rating": 5.0})
    assert response.status_code == 404


def test_delete_movie_and_second_delete_404(client, created_movie):
    movie_id = created_movie["id"]
    assert client.delete(f"/movies/{movie_id}").status_code == 204
    assert client.get(f"/movies/{movie_id}").status_code == 404
    assert client.delete(f"/movies/{movie_id}").status_code == 404


# ------------------------------------------------------------------- cache


def test_cache_hit_miss_and_invalidation(client, created_movie):
    cache = get_cache()
    movie_id = created_movie["id"]

    cache.reset_stats()
    client.get(f"/movies/{movie_id}")   # miss -> БД -> запись в кэш
    client.get(f"/movies/{movie_id}")   # hit из кэша
    assert cache.misses >= 1
    assert cache.hits >= 1

    # PATCH инвалидирует кэш, следующий GET снова идёт в БД (miss)
    client.patch(f"/movies/{movie_id}", json={"rating": 9.2})
    misses_before = cache.misses
    client.get(f"/movies/{movie_id}")
    assert cache.misses == misses_before + 1
