"""Пакет Blueprint-маршрутов."""
from app.routes.api import api  # noqa: F401
from app.routes.web import web  # noqa: F401

__all__ = ["web", "api"]
