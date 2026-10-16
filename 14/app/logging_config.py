"""Настройка журналирования (п. 39 методички)."""
from __future__ import annotations

import logging
import sys

from .config import get_settings

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_configured = False


def configure_logging() -> None:
    """Настраивает корневой логгер один раз за время жизни процесса."""
    global _configured
    if _configured:
        return

    settings = get_settings()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(settings.log_level)

    # uvicorn.access дублирует наш middleware — отключаем, чтобы не шумел.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    _configured = True
