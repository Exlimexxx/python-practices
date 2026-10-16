"""Точка входа FastAPI-приложения «Кинотеатр — фильмы» (вариант 4).

Запуск::

    uvicorn app.main:app --host 127.0.0.1 --port 8014 --reload

Документация: http://127.0.0.1:8014/docs и /redoc, схема — /openapi.json.
"""
from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .cache import close_cache, get_cache_kind, init_cache
from .config import get_settings
from .database import init_db
from .exceptions import AppError, error_payload
from .logging_config import configure_logging
from .routers.movies import router as movies_router

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управляет ресурсами: БД и кэш поднимаются при старте, кэш закрывается при остановке."""
    configure_logging()
    logger.info("Запуск %s v%s (env=%s)", settings.app_name, settings.app_version, settings.app_env)
    init_db()
    await init_cache()
    logger.info("Активный кэш: %s", get_cache_kind())
    yield
    await close_cache()
    logger.info("Приложение остановлено")


def create_app() -> FastAPI:
    """Фабрика приложения (удобно для тестов)."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "REST API кинотеатра (вариант 4). Ресурс /movies: CRUD, фильтрация, "
            "поиск, сортировка, пагинация, статистика и кэширование через Redis."
        ),
        lifespan=lifespan,
    )

    # -------------------------------------------------------------- middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """Логирует метод, URL, статус и время выполнения (п. 39 методички)."""
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            elapsed = (time.perf_counter() - started) * 1000
            logger.exception("%s %s -> 500 (%.1f ms)", request.method, request.url.path, elapsed)
            raise
        elapsed = (time.perf_counter() - started) * 1000
        log = logger.warning if response.status_code >= 400 else logger.info
        log(
            "%s %s%s -> %s (%.1f ms)",
            request.method,
            request.url.path,
            f"?{request.url.query}" if request.url.query else "",
            response.status_code,
            elapsed,
        )
        response.headers["X-Process-Time-ms"] = f"{elapsed:.2f}"
        return response

    # ------------------------------------------------------- обработчики ошибок
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        logger.warning("Доменная ошибка %s: %s", exc.code, exc.message)
        return JSONResponse(status_code=exc.status_code, content=exc.to_payload())

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        # Приводим 422 к единому формату.
        logger.warning("Ошибка валидации %s: %s", request.url.path, exc.errors())
        return JSONResponse(
            status_code=422,
            content=error_payload("validation_error", "Ошибка валидации входных данных", exc.errors()),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        code = "not_found" if exc.status_code == 404 else "http_error"
        return JSONResponse(
            status_code=exc.status_code,
            content=error_payload(code, str(exc.detail)),
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception):
        # Клиенту не отдаём traceback (п. 40 методички).
        logger.exception("Необработанная ошибка на %s", request.url.path)
        return JSONResponse(
            status_code=500,
            content=error_payload("internal_error", "Внутренняя ошибка сервера"),
        )

    # ------------------------------------------------------------------ routes
    app.include_router(movies_router)

    @app.get("/", tags=["service"], summary="Корневой эндпоинт")
    def root() -> dict:
        return {
            "service": settings.app_name,
            "version": settings.app_version,
            "variant": 4,
            "resource": "/movies",
            "docs": "/docs",
            "openapi": "/openapi.json",
        }

    @app.get("/health", tags=["service"], summary="Проверка состояния")
    def health() -> dict:
        return {"status": "ok", "cache": get_cache_kind()}

    return app


app = create_app()
