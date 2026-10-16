"""Точка входа приложения: python run.py (Application Factory, п. 16)."""
from __future__ import annotations

import logging

from app import create_app
from app.config import Settings

logger = logging.getLogger(__name__)


def main() -> None:
    """Создаёт приложение и запускает встроенный сервер разработки."""
    app = create_app()
    settings: Settings = app.config["SETTINGS"]
    logger.info("Запуск сервера на http://%s:%s (debug=%s)", settings.HOST, settings.PORT, settings.DEBUG)
    app.run(host=settings.HOST, port=settings.PORT, debug=settings.DEBUG, use_reloader=False)


if __name__ == "__main__":
    main()
