"""Общие фикстуры тестов: приложение, клиент, пользователи, сервисы."""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import Settings
from app.database import create_engine_from_url, create_session_factory, init_database
from app.main import create_app
from app.models import User
from app.repositories.booking_repository import BookingRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.room_repository import RoomRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserRegister
from app.services.booking_service import BookingService
from app.services.payment_service import PaymentService
from app.services.room_service import RoomService
from app.services.user_service import UserService
from tests.helpers import booking_payload, future_period, register_and_login, room_payload

ADMIN_EMAIL = "admin@hotel.ru"
ADMIN_PASSWORD = "admin-pass-12345"
GUEST_EMAIL = "guest@example.com"
GUEST_PASSWORD = "guest-pass-12345"
SECOND_GUEST_EMAIL = "second@example.com"
SECOND_GUEST_PASSWORD = "second-pass-12345"
UNIT_EMAIL = "unit@example.com"
UNIT_PASSWORD = "unit-pass-12345"


@pytest.fixture()
def settings(tmp_path: Path) -> Settings:
    return Settings(
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        jwt_secret="test-secret-test-secret-test-secret",
        access_token_ttl_minutes=30,
        log_level="WARNING",
        admin_email=ADMIN_EMAIL,
        admin_password=ADMIN_PASSWORD,
    )


@pytest.fixture()
def app(settings: Settings) -> Iterator[FastAPI]:
    application = create_app(settings)
    yield application
    application.state.engine.dispose()


@pytest.fixture()
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def admin(client: TestClient) -> dict[str, Any]:
    login = client.post(
        "/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert login.status_code == 200, login.text
    return {
        "email": ADMIN_EMAIL,
        "headers": {"Authorization": f"Bearer {login.json()['access_token']}"},
    }


@pytest.fixture()
def guest(client: TestClient) -> dict[str, Any]:
    return register_and_login(client, email=GUEST_EMAIL, password=GUEST_PASSWORD)


@pytest.fixture()
def second_guest(client: TestClient) -> dict[str, Any]:
    return register_and_login(
        client,
        email=SECOND_GUEST_EMAIL,
        password=SECOND_GUEST_PASSWORD,
        full_name="Мария Сидорова",
    )


@pytest.fixture()
def room(client: TestClient, admin: dict[str, Any]) -> dict[str, Any]:
    response = client.post("/rooms", json=room_payload(), headers=admin["headers"])
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture()
def booking(
    client: TestClient,
    guest: dict[str, Any],
    room: dict[str, Any],
) -> dict[str, Any]:
    check_in, check_out = future_period()
    response = client.post(
        "/bookings",
        json=booking_payload(room["id"], check_in, check_out),
        headers=guest["headers"],
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture()
def session(settings: Settings) -> Iterator[Session]:
    """Сессия для модульных тестов сервисов и репозиториев."""
    engine = create_engine_from_url(settings.database_url)
    init_database(engine)
    factory = create_session_factory(engine)
    with factory() as db_session:
        yield db_session
    engine.dispose()


@pytest.fixture()
def user_service(session: Session, settings: Settings) -> UserService:
    return UserService(session, UserRepository(session), settings)


@pytest.fixture()
def room_service(session: Session) -> RoomService:
    return RoomService(session, RoomRepository(session), BookingRepository(session))


@pytest.fixture()
def booking_service(session: Session) -> BookingService:
    return BookingService(
        session,
        BookingRepository(session),
        RoomRepository(session),
        PaymentRepository(session),
    )


@pytest.fixture()
def payment_service(session: Session) -> PaymentService:
    return PaymentService(session, PaymentRepository(session), BookingRepository(session))


@pytest.fixture()
def actor(session: Session, user_service: UserService) -> User:
    """Гость на уровне сервисов (ORM-сущность)."""
    created = user_service.register(
        UserRegister(email=UNIT_EMAIL, full_name="Юнит Тестов", password=UNIT_PASSWORD)
    )
    user = UserRepository(session).get(created.id)
    assert user is not None
    return user
