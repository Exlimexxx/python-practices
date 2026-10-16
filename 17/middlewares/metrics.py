"""Пользовательский middleware: логирование и подсчёт обновлений."""
import logging
from collections import Counter
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware

logger = logging.getLogger(__name__)


class MetricsMiddleware(BaseMiddleware):
    def __init__(self) -> None:
        self.counts: Counter[int] = Counter()

    async def __call__(
        self,
        handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is not None:
            self.counts[user.id] += 1
            logger.info("Update user_id=%s count=%s", user.id, self.counts[user.id])
        return await handler(event, data)
