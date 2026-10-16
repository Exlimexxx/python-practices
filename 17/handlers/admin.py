from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from services.cinema import CinemaService

router = Router()


def is_admin(user_id: int, admin_ids: set[int]) -> bool:
    return user_id in admin_ids


def parse_movie_payload(text: str) -> tuple[str, str, int, float]:
    parts = [part.strip() for part in text.split("|")]
    if len(parts) != 4:
        raise ValueError("Формат: Название|Жанр|Длительность|Рейтинг")
    return parts[0], parts[1], int(parts[2]), float(parts[3])


@router.message(Command("addmovie"))
async def add_movie(message: Message, service: CinemaService, admin_ids: set[int]) -> None:
    if message.from_user is None or not is_admin(message.from_user.id, admin_ids):
        await message.answer("Операция доступна только администратору.")
        return
    try:
        if not message.text or " " not in message.text:
            raise ValueError("Укажите данные после команды.")
        payload = parse_movie_payload(message.text.split(" ", 1)[1])
        movie_id = service.add_movie(*payload)
        await message.answer(f"Фильм добавлен. ID: {movie_id}.")
    except (ValueError, TypeError) as exc:
        await message.answer(f"Ошибка: {exc}")


@router.message(Command("editmovie"))
async def edit_movie(message: Message, service: CinemaService, admin_ids: set[int]) -> None:
    if message.from_user is None or not is_admin(message.from_user.id, admin_ids):
        await message.answer("Операция доступна только администратору.")
        return
    try:
        if not message.text or " " not in message.text:
            raise ValueError("Формат: ID|Название|Жанр|Длительность|Рейтинг")
        parts = message.text.split(" ", 1)[1].split("|")
        if len(parts) != 5:
            raise ValueError("Формат: ID|Название|Жанр|Длительность|Рейтинг")
        service.update_movie(int(parts[0]), parts[1], parts[2], int(parts[3]), float(parts[4]))
        await message.answer("Карточка фильма изменена.")
    except (ValueError, LookupError) as exc:
        await message.answer(f"Ошибка: {exc}")


@router.message(Command("deletemovie"))
async def delete_movie(message: Message, service: CinemaService, admin_ids: set[int]) -> None:
    if message.from_user is None or not is_admin(message.from_user.id, admin_ids):
        await message.answer("Операция доступна только администратору.")
        return
    try:
        movie_id = int((message.text or "").split(maxsplit=1)[1])
        service.delete_movie(movie_id)
        await message.answer("Фильм удалён из каталога.")
    except (ValueError, IndexError, LookupError) as exc:
        await message.answer(f"Ошибка удаления: {exc}")
