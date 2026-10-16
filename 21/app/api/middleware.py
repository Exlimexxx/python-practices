"""Промежуточное ПО журналирования HTTP-запросов."""
from __future__ import annotations

import logging
import time

from fastapi import FastAPI, Request

logger = logging.getLogger("app.access")


def register_request_logging(app: FastAPI) -> None:
    @app.middleware("http")
    async def log_request(request: Request, call_next):
        started = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - started) * 1000
        logger.info(
            "%s %s status=%s duration=%.1fms",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response
