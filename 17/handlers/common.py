from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from keyboards.menu import main_menu
from services.cinema import CinemaService
from states.booking import BookingStates

router = Router()


@router.message(Command("start"))
async def start(message: Message) -> None:
    await message.answer(
        "Добро пожаловать в информационную систему кинотеатра! Выберите раздел меню.",
        reply_markup=main_menu(),
    )


@router.message(Command("help"))
async def help_command(message: Message) -> None:
    await message.answer(
        "/start — главное меню\n/help — помощь\n/cancel — отменить текущий сценарий\n"
        "/movies — каталог фильмов\n/schedule — расписание\n/book — бронирование\n"
        "Администратор: /addmovie, /editmovie, /deletemovie."
    )


@router.message(Command("cancel"))
async def cancel_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Текущая операция отменена.", reply_markup=main_menu())


@router.message(lambda m: m.text == "Фильмы")
async def menu_movies(message: Message, service: CinemaService) -> None:
    from keyboards.menu import movie_buttons
    items = service.movies()
    await message.answer("Каталог фильмов:", reply_markup=movie_buttons(items))


@router.message(lambda m: m.text == "Расписание")
async def menu_schedule(message: Message, service: CinemaService) -> None:
    from keyboards.menu import screening_buttons
    await message.answer("Ближайшие сеансы:", reply_markup=screening_buttons(service.schedule()))


@router.message(lambda m: m.text == "Найти фильм")
async def menu_search(message: Message, state: FSMContext) -> None:
    await state.set_state(SearchState.query)
    await message.answer("Введите часть названия фильма для поиска:")


class SearchState(StatesGroup):
    """Состояние ввода строки поиска."""
    query = State()


@router.message(SearchState.query)
async def search_movie(message: Message, state: FSMContext, service: CinemaService) -> None:
    result = service.search(message.text or "")
    await state.clear()
    if not result:
        await message.answer("Фильмы не найдены.")
        return
    from keyboards.menu import movie_buttons
    await message.answer("Результаты поиска:", reply_markup=movie_buttons(result))
