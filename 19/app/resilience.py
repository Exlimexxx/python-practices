"""Retry и Circuit Breaker для межсервисных HTTP-запросов."""
from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")


class CircuitOpenError(RuntimeError):
    pass


async def retry_async(
    operation: Callable[[], Awaitable[T]], attempts: int = 3,
    base_delay: float = 0.02,
) -> T:
    """Повторяет временно неудачный вызов с ограниченной экспоненциальной задержкой."""
    if attempts < 1:
        raise ValueError("Число попыток должно быть не меньше 1")
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            return await operation()
        except Exception as exc:
            last_error = exc
            if attempt + 1 < attempts:
                await asyncio.sleep(base_delay * (2 ** attempt))
    assert last_error is not None
    raise last_error


class CircuitBreaker:
    """Упрощённый автомат CLOSED → OPEN → HALF_OPEN → CLOSED."""

    def __init__(self, failure_threshold: int = 2, reset_timeout: float = 2.0) -> None:
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failures = 0
        self.opened_at: float | None = None
        self.state = "CLOSED"

    async def call(self, operation: Callable[[], Awaitable[T]]) -> T:
        now = time.monotonic()
        if self.state == "OPEN":
            if self.opened_at is None or now - self.opened_at < self.reset_timeout:
                raise CircuitOpenError("Circuit Breaker находится в состоянии OPEN")
            self.state = "HALF_OPEN"
        try:
            result = await operation()
        except Exception:
            self.failures += 1
            if self.failures >= self.failure_threshold or self.state == "HALF_OPEN":
                self.state = "OPEN"
                self.opened_at = time.monotonic()
            raise
        self.failures = 0
        self.opened_at = None
        self.state = "CLOSED"
        return result
