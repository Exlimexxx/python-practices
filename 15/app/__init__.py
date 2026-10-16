"""Фабрика Flask-приложения (паттерн Application Factory, п. 16 методички).

Лабораторная работа №15, вариант 4 «Отель»: сущности Room, Guest, Booking.
"""
from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path
from typing import Any

from flask import Flask, g, jsonify, render_template, request

from app.config import Settings
from app.database import Database
from app.exceptions import HotelError, NotFoundError
from app.logging_config import configure_logging
from app.seed import seed_database

logger = logging.getLogger(__name__)

__all__ = ["create_app"]


def create_app(config_overrides: dict[str, Any] | None = None) -> Flask:
    """Создаёт и настраивает экземпляр Flask-приложения.

    :param config_overrides: точечные переопределения настроек
        (используются в тестах, например DATABASE_URL и TESTING).
    """
    settings = Settings.from_env(**(config_overrides or {}))
    configure_logging(settings.LOG_LEVEL, settings.LOG_FILE, settings.BASE_DIR)

    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.update(settings.as_flask_config())

    database = Database(settings.DATABASE_URL, echo=settings.SQL_ECHO, base_dir=settings.BASE_DIR)
    database.create_all()
    app.extensions["database"] = database

    if settings.SEED_DEMO:
        with database.session_scope() as session:
            created = seed_database(session)
        logger.info("Демонстрационные данные загружены: %s", created)

    _register_blueprints(app)
    _register_request_hooks(app, database)
    _register_error_handlers(app)

    logger.info("Приложение создано: env=%s, db=%s", settings.FLASK_ENV, settings.DATABASE_URL)
    return app


def _register_blueprints(app: Flask) -> None:
    """Подключает HTML- и API-Blueprint."""
    from app.routes.api import api
    from app.routes.web import web

    app.register_blueprint(web)
    app.register_blueprint(api)
    logger.debug("Blueprint-ы зарегистрированы")


def _register_request_hooks(app: Flask, database: Database) -> None:
    """Открывает/закрывает сессию БД и журналирует HTTP-запросы."""

    @app.before_request
    def _open_session() -> None:
        g.db_session = database.get_session()
        g.request_started = time.perf_counter()
        g.request_id = uuid.uuid4().hex[:8]

    @app.after_request
    def _log_request(response: Any) -> Any:
        duration_ms = (time.perf_counter() - getattr(g, "request_started", time.perf_counter())) * 1000
        logger.info(
            "HTTP %s %s -> %s (%.2f мс) [%s]",
            request.method, request.full_path.rstrip("?"), response.status_code, duration_ms,
            getattr(g, "request_id", "-"),
        )
        return response

    @app.teardown_appcontext
    def _close_session(exception: BaseException | None) -> None:
        if exception is not None:
            logger.warning("Запрос завершился исключением: %s", exception)
        database.remove_session()


def _wants_json() -> bool:
    """Определяет, нужно ли вернуть JSON, а не HTML-страницу."""
    if request.path.startswith("/api"):
        return True
    return request.accept_mimetypes.best == "application/json"


def _register_error_handlers(app: Flask) -> None:
    """Регистрирует обработчики ошибок (HTML и JSON)."""

    @app.errorhandler(HotelError)
    def _handle_hotel_error(error: HotelError) -> Any:
        logger.warning("Ошибка приложения %s: %s", type(error).__name__, error.message)
        if _wants_json():
            return jsonify(error.to_dict()), error.status_code
        template = "404.html" if error.status_code == 404 else "error.html"
        return render_template(template, error=error, status=error.status_code), error.status_code

    @app.errorhandler(NotFoundError)
    def _handle_not_found(error: NotFoundError) -> Any:
        if _wants_json():
            return jsonify(error.to_dict()), 404
        return render_template("404.html", error=error, status=404), 404

    @app.errorhandler(405)
    def _method_not_allowed(error: Any) -> Any:
        logger.info("405: %s %s", request.method, request.path)
        if _wants_json():
            return jsonify({"error": "MethodNotAllowed", "message": "Метод не поддерживается",
                            "status": 405}), 405
        return render_template("error.html", error=None, status=405), 405

    @app.errorhandler(404)
    def _page_not_found(error: Any) -> Any:
        logger.info("404: %s", request.path)
        if _wants_json():
            return jsonify({"error": "NotFound", "message": "Ресурс не найден", "status": 404}), 404
        return render_template("404.html", error=None, status=404), 404

    @app.errorhandler(500)
    def _internal_error(error: Any) -> Any:
        logger.exception("Внутренняя ошибка: %s", error)
        if _wants_json():
            return jsonify({"error": "InternalServerError", "message": "Внутренняя ошибка сервера",
                            "status": 500}), 500
        return render_template("error.html", error=None, status=500), 500
