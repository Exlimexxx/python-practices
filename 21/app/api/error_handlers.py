"""Централизованная обработка ошибок: единый формат ответа API."""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.exceptions import AppError

logger = logging.getLogger(__name__)


def _validation_details(exc: RequestValidationError) -> list[dict]:
    details = []
    for error in exc.errors():
        location = ".".join(str(part) for part in error.get("loc", ()) if part != "body")
        details.append(
            {
                "field": location or "body",
                "message": error.get("msg", "Некорректное значение"),
                "type": error.get("type", "value_error"),
            }
        )
    return details


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        if exc.status_code >= 500:
            logger.exception("Ошибка приложения: %s", exc.code)
        else:
            logger.warning("Ошибка запроса %s: %s", exc.code, exc.message)
        return JSONResponse(status_code=exc.status_code, content=exc.to_dict())

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": "VALIDATION_ERROR",
                "message": "Некорректные данные запроса",
                "details": {"errors": _validation_details(exc)},
            },
        )

    @app.exception_handler(IntegrityError)
    async def handle_integrity_error(_: Request, exc: IntegrityError) -> JSONResponse:
        logger.warning("Нарушение ограничений БД: %s", exc.orig)
        return JSONResponse(
            status_code=409,
            content={
                "error": "DATA_CONFLICT",
                "message": "Операция конфликтует с текущим состоянием данных",
            },
        )

    @app.exception_handler(SQLAlchemyError)
    async def handle_database_error(_: Request, exc: SQLAlchemyError) -> JSONResponse:
        logger.exception("Ошибка доступа к базе данных")
        return JSONResponse(
            status_code=503,
            content={
                "error": "DATABASE_UNAVAILABLE",
                "message": "База данных временно недоступна",
            },
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Необработанная ошибка: %s", exc)
        return JSONResponse(
            status_code=500,
            content={
                "error": "INTERNAL_ERROR",
                "message": "Внутренняя ошибка сервера",
            },
        )
