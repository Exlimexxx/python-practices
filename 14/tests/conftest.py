"""Общие фикстуры pytest.

Переменные окружения выставляются ДО импорта приложения, потому что движок
SQLAlchemy создаётся на этапе импорта app.database.
"""
from __future__ import annotations

import os

# Тестовая конфигурация: отдельная БД и принудительный in-memory кэш.
os.environ["CACHE_BACKEND"] = "memory"
os.environ["DATABASE_URL"] = "sqlite:///./test_movies.db"
os.environ["LOG_LEVEL"] = "WARNING"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.cache import get_cache  # noqa: E402
from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def client():
    """TestClient с чистой БД и сброшенной статистикой кэша."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as test_client:
        cache = get_cache()
        if hasattr(cache, "reset_stats"):
            cache.reset_stats()
        yield test_client


@pytest.fixture()
def sample_movie() -> dict:
    """Эталонный корректный фильм."""
    return {
        "title": "Начало",
        "director": "Кристофер Нолан",
        "year": 2010,
        "genre": "фантастика",
        "duration": 148,
        "rating": 8.8,
        "description": "Вор проникает в сны, чтобы украсть идею.",
    }


@pytest.fixture()
def created_movie(client, sample_movie) -> dict:
    """Фильм, уже созданный в БД."""
    response = client.post("/movies", json=sample_movie)
    assert response.status_code == 201
    return response.json()
