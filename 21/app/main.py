"""Точка входа приложения «Бронирование гостиницы».

Запуск:
    uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000
или:
    python -m app.main
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.error_handlers import register_exception_handlers
from app.api.middleware import register_request_logging
from app.api.routes import auth, bookings, health, payments, reports, rooms, users
from app.config import Settings, get_settings
from app.database import create_engine_from_url, create_session_factory, init_database
from app.logging_config import configure_logging
from app.repositories.user_repository import UserRepository
from app.schemas.common import ErrorResponse
from app.services.user_service import UserService

logger = logging.getLogger(__name__)

DESCRIPTION = """
Система бронирования гостиницы (итоговый проект, вариант 4).

Слои приложения: HTTP-слой (`app/api`) → сервисы (`app/services`) →
репозитории (`app/repositories`) → SQLAlchemy → база данных.

Основные возможности: управление номерным фондом, бронирование с проверкой
пересечения периодов, оплата и возврат средств, роли USER/ADMIN, статистика.
"""


def bootstrap_admin(app: FastAPI) -> None:
    """Создать администратора из переменных окружения при первом запуске."""
    settings: Settings = app.state.settings
    if not settings.admin_email or not settings.admin_password:
        return
    session = app.state.session_factory()
    try:
        service = UserService(session, UserRepository(session), settings)
        service.ensure_admin(
            email=settings.admin_email,
            password=settings.admin_password,
            full_name=settings.admin_full_name,
        )
    except Exception:  # pragma: no cover - защита от сбоя начальной настройки
        session.rollback()
        logger.exception("Не удалось создать администратора по умолчанию")
    finally:
        session.close()


def create_app(settings: Settings | None = None) -> FastAPI:
    """Собрать приложение: конфигурация, БД, маршруты и обработчики ошибок."""
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    engine = create_engine_from_url(settings.database_url, echo=settings.sql_echo)
    session_factory = create_session_factory(engine)
    init_database(engine)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        logger.info("Приложение запущено, база данных: %s", settings.database_url)
        yield
        engine.dispose()
        logger.info("Приложение остановлено")

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=DESCRIPTION,
        lifespan=lifespan,
        responses={500: {"model": ErrorResponse, "description": "Внутренняя ошибка"}},
    )
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = session_factory

    register_request_logging(app)
    register_exception_handlers(app)

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(rooms.router)
    app.include_router(bookings.router)
    app.include_router(payments.router)
    app.include_router(reports.router)

    bootstrap_admin(app)
    return app


def main() -> None:  # pragma: no cover - ручной запуск
    import uvicorn

    uvicorn.run(create_app(), host="0.0.0.0", port=8000)


if __name__ == "__main__":  # pragma: no cover - ручной запуск
    main()
