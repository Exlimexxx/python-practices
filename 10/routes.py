# -*- coding: utf-8 -*-
"""HTTP-слой (Routes / Controller) REST API кинотеатра.

Модуль содержит только разбор HTTP-запроса и вызовы MovieService.
Бизнес-логики здесь нет — это требование методички (Route -> Service -> Repository).
"""
from __future__ import annotations

from typing import Any

from flask import Blueprint, Response, jsonify, request, url_for

from exceptions import ValidationError
from schemas import (
    movies_to_list,
    parse_movie_id,
    parse_optional_float,
    parse_optional_str,
    parse_order,
    parse_sort_field,
)
from service import MovieService


def create_movies_blueprint(service: MovieService) -> Blueprint:
    """Собирает blueprint с endpoints ресурса /movies.

    :param service: экземпляр бизнес-сервиса
    """
    bp = Blueprint("movies", __name__)

    def json_body() -> dict[str, Any]:
        """Читает JSON-тело запроса (400, если это не корректный JSON-объект)."""
        data = request.get_json(silent=True, force=True)
        if data is None:
            raise ValidationError("Тело запроса должно содержать корректный JSON")
        return data

    @bp.get("/movies")
    def list_movies() -> tuple[Response, int]:
        """GET /movies — список фильмов (query: genre, min_rating, max_price, sort, order)."""
        genre = parse_optional_str(request.args.get("genre"))
        min_rating = parse_optional_float(request.args.get("min_rating"), "min_rating")
        max_price = parse_optional_float(request.args.get("max_price"), "max_price")
        sort = parse_sort_field(request.args.get("sort"))
        order = parse_order(request.args.get("order"))

        movies = service.list_movies(
            genre=genre,
            min_rating=min_rating,
            max_price=max_price,
            sort=sort,
            order=order,
        )
        return jsonify(movies_to_list(movies)), 200

    @bp.get("/movies/by-genre")
    def movies_by_genre() -> tuple[Response, int]:
        """GET /movies/by-genre?genre=... — специализированная операция (фильмы по жанру)."""
        payload = service.get_movies_by_genre(parse_optional_str(request.args.get("genre")))
        return jsonify(payload), 200

    @bp.post("/movies")
    def create_movie() -> Response:
        """POST /movies — создание фильма (201 Created + заголовок Location)."""
        movie = service.create_movie(json_body())
        response = jsonify(movie.to_dict())
        response.status_code = 201
        response.headers["Location"] = url_for("movies.get_movie", movie_id=movie.id)
        return response

    @bp.get("/movies/<movie_id>")
    def get_movie(movie_id: str) -> tuple[Response, int]:
        """GET /movies/{id} — получение фильма по path-параметру."""
        return jsonify(service.get_movie(parse_movie_id(movie_id)).to_dict()), 200

    @bp.put("/movies/<movie_id>")
    def replace_movie(movie_id: str) -> tuple[Response, int]:
        """PUT /movies/{id} — полное изменение фильма."""
        movie = service.replace_movie(parse_movie_id(movie_id), json_body())
        return jsonify(movie.to_dict()), 200

    @bp.patch("/movies/<movie_id>")
    def patch_movie(movie_id: str) -> tuple[Response, int]:
        """PATCH /movies/{id} — частичное изменение фильма."""
        movie = service.patch_movie(parse_movie_id(movie_id), json_body())
        return jsonify(movie.to_dict()), 200

    @bp.delete("/movies/<movie_id>")
    def delete_movie(movie_id: str) -> tuple[Response, int]:
        """DELETE /movies/{id} — удаление фильма (204 No Content)."""
        service.delete_movie(parse_movie_id(movie_id))
        return "", 204

    return bp
