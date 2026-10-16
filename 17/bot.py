"""Точка входа Telegram-бота. Токен берётся только из окружения BOT_TOKEN."""
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from database.repository import CinemaRepository
from handlers import admin, booking, common, movies
from middlewares.metrics import MetricsMiddleware
from services.cinema import CinemaService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


async def main() -> None:
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("Задайте токен Telegram-бота в переменной окружения BOT_TOKEN")
    db_path = os.getenv("CINEMA_DB_PATH", "cinema.db")
    repo = CinemaRepository(Path(db_path))
    service = CinemaService(repo)
    admin_ids = {int(value) for value in os.getenv("ADMIN_IDS", "").split(",") if value.strip().isdigit()}

    bot = Bot(token=token)
    dp = Dispatcher(storage=MemoryStorage())
    dp.update.middleware(MetricsMiddleware())
    dp["service"] = service
    dp["admin_ids"] = admin_ids
    dp.include_routers(common.router, movies.router, booking.router, admin.router)
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        repo.close()


if __name__ == "__main__":
    asyncio.run(main())
