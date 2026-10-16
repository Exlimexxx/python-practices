"""Настройка стандартного модуля logging (требование п. 25 методички)."""
from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def configure_logging(level: str = "INFO", log_file: str | None = None, base_dir: Path | None = None) -> None:
    """Настраивает корневой логгер: консоль + (опционально) файл с ротацией."""
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(numeric_level)
    # Удаляем прежние обработчики, чтобы не дублировать строки в тестах.
    for handler in list(root.handlers):
        root.removeHandler(handler)

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    console = logging.StreamHandler(stream=sys.stdout)
    console.setFormatter(formatter)
    console.setLevel(numeric_level)
    root.addHandler(console)

    if log_file:
        path = Path(log_file)
        if not path.is_absolute() and base_dir is not None:
            path = base_dir / path
        path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(path, maxBytes=512_000, backupCount=3, encoding="utf-8")
        file_handler.setFormatter(formatter)
        file_handler.setLevel(numeric_level)
        root.addHandler(file_handler)

    # Werkzeug пишет собственный access-лог; оставляем его на уровне WARNING,
    # чтобы не дублировать наш журнал HTTP-запросов.
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    logging.getLogger("app").info("Логирование настроено: уровень=%s, файл=%s", level.upper(), log_file or "нет")
