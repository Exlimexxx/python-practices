# -*- coding: utf-8 -*-
"""Общие фикстуры pytest для тестов REST API кинотеатра."""
from __future__ import annotations

import pytest
from flask import Flask
from flask.testing import FlaskClient

from app import create_app
from repository import MovieRepository, seed_movies
from service import MovieService


@pytest.fixture()
def application() -> Flask:
    """Новый экземпляр приложения с начальным набором фильмов для каждого теста."""
    app = create_app()
    app.config.update(TESTING=True)
    return app


@pytest.fixture()
def client(application: Flask) -> FlaskClient:
    """Тестовый HTTP-клиент Flask (реальный сервер не запускается)."""
    return application.test_client()


@pytest.fixture()
def service() -> MovieService:
    """Сервис с чистым хранилищем начальных данных."""
    return MovieService(MovieRepository(seed_movies()))
