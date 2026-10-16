from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from keyboards.menu import movie_buttons, screening_buttons
from services.cinema import CinemaService

router = Router()


@router.message(Command("movies"))
async def list_movies(message: Message, service: CinemaService) -> None:
    await message.answer("Каталог фильмов:", reply_markup=movie_buttons(service.movies()))


@router.message(Command("schedule"))
async def show_schedule(message: Message, service: CinemaService) -> None:
    await message.answer("Расписание сеансов:", reply_markup=screening_buttons(service.schedule()))


@router.callback_query(F.data.startswith("movie:"))
async def show_movie(callback: CallbackQuery, service: CinemaService) -> None:
    try:
        movie = service.movie(int(callback.data.split(":", 1)[1]))
        await callback.message.answer(
            f"{movie['title']}\nЖанр: {movie['genre']}\nПродолжительность: {movie['duration']} мин.\n"
            f"Рейтинг: {movie['rating']:.1f}/10"
        )
    except (ValueError, LookupError):
        await callback.message.answer("Фильм не найден или идентификатор некорректен.")
    await callback.answer()
