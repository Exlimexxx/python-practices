# -*- coding: utf-8 -*-
"""Точка входа Flask-приложения «Кинотеатр» (лабораторная работа №10, вариант 4).

Запуск сервера::

    python app.py            # http://127.0.0.1:5010

Архитектура: HTTP (routes) -> Service -> Repository.
Данные хранятся в памяти, БД и ORM не используются.
"""
from __future__ import annotations

import logging
import time

from flask import Flask, Response, g, jsonify, request

from exceptions import ApiError
from repository import MovieRepository, seed_movies
from routes import create_movies_blueprint
from service import MovieService

LOGGER = logging.getLogger("cinema.api")
DEFAULT_PORT = 5010


def register_error_handlers(app: Flask) -> None:
    """Регистрирует обработчики ошибок с единым форматом {"error": ..., "code": ...}."""

    @app.errorhandler(ApiError)
    def handle_api_error(error: ApiError) -> tuple[Response, int]:
        """Исключения предметной области (400 / 404 / 405)."""
        LOGGER.warning("Ошибка API: %s", error)
        return jsonify(error.to_dict()), error.status_code

    @app.errorhandler(404)
    def handle_not_found(error: Exception) -> tuple[Response, int]:
        """Маршрут не найден."""
        return jsonify({"error": "Маршрут не найден", "code": "NOT_FOUND"}), 404

    @app.errorhandler(405)
    def handle_method_not_allowed(error: Exception) -> tuple[Response, int]:
        """HTTP-метод не поддерживается ресурсом."""
        return (
            jsonify({"error": "HTTP-метод не поддерживается для данного ресурса", "code": "METHOD_NOT_ALLOWED"}),
            405,
        )

    @app.errorhandler(400)
    def handle_bad_request(error: Exception) -> tuple[Response, int]:
        """Некорректный HTTP-запрос."""
        return jsonify({"error": "Некорректный запрос", "code": "BAD_REQUEST"}), 400

    @app.errorhandler(Exception)
    def handle_internal_error(error: Exception) -> tuple[Response, int]:
        """Любая необработанная ошибка — 500."""
        LOGGER.exception("Необработанная ошибка: %s", error)
        return jsonify({"error": "Внутренняя ошибка сервера", "code": "INTERNAL_ERROR"}), 500


def register_middleware(app: Flask) -> None:
    """Дополнительное задание 4: журналирование запроса и времени выполнения."""

    @app.before_request
    def before_request() -> None:
        """Запоминает время начала обработки запроса."""
        g.request_started = time.perf_counter()

    @app.after_request
    def after_request(response: Response) -> Response:
        """Пишет строку вида: GET /movies -> 200 -> 12.3 ms."""
        started = getattr(g, "request_started", time.perf_counter())
        duration_ms = (time.perf_counter() - started) * 1000
        LOGGER.info(
            "%s %s -> %s -> %.1f ms",
            request.method,
            request.full_path.rstrip("?"),
            response.status_code,
            duration_ms,
        )
        response.headers["X-API-Version"] = "1.0"
        return response


def create_app(repository: MovieRepository | None = None) -> Flask:
    """Фабрика приложения (используется и сервером, и тестами).

    :param repository: готовое хранилище; по умолчанию создаётся с начальными данными
    """
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        )

    repository = repository if repository is not None else MovieRepository(seed_movies())
    service = MovieService(repository)

    app = Flask(__name__)
    app.json.ensure_ascii = False  # кириллица в JSON без экранирования \uXXXX
    app.config["SERVICE"] = service
    app.logger.setLevel(logging.INFO)

    register_error_handlers(app)
    register_middleware(app)
    app.register_blueprint(create_movies_blueprint(service))
    return app


app = create_app()


if __name__ == "__main__":
    print(f"Сервер кинотеатра запущен: http://127.0.0.1:{DEFAULT_PORT}/movies")
    app.run(host="127.0.0.1", port=DEFAULT_PORT, debug=False, use_reloader=False)
