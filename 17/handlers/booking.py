from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from keyboards.menu import screening_buttons
from services.cinema import CinemaService
from states.booking import BookingStates

router = Router()


@router.message(Command("book"))
@router.message(F.text == "Забронировать билет")
async def begin_booking(message: Message, state: FSMContext, service: CinemaService) -> None:
    await state.set_state(BookingStates.choose_screening)
    await message.answer("Выберите сеанс: введите его номер из списка.", reply_markup=screening_buttons(service.schedule()))


@router.callback_query(F.data.startswith("booking:"))
async def choose_screening_button(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        screening_id = int(callback.data.split(":", 1)[1])
    except (ValueError, AttributeError):
        await callback.answer("Некорректный сеанс", show_alert=True)
        return
    await state.update_data(screening_id=screening_id, user_id=callback.from_user.id)
    await state.set_state(BookingStates.enter_row)
    await callback.message.answer("Введите номер ряда (положительное целое число):")
    await callback.answer()


@router.message(BookingStates.choose_screening)
async def choose_screening_text(message: Message, state: FSMContext) -> None:
    try:
        screening_id = int(message.text or "")
        if screening_id <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Номер сеанса должен быть положительным целым числом.")
        return
    await state.update_data(screening_id=screening_id, user_id=message.from_user.id)
    await state.set_state(BookingStates.enter_row)
    await message.answer("Введите номер ряда:")


@router.message(BookingStates.enter_row)
async def enter_row(message: Message, state: FSMContext) -> None:
    try:
        row = int(message.text or "")
        if row <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Ряд должен быть положительным целым числом. Повторите ввод.")
        return
    await state.update_data(row=row)
    await state.set_state(BookingStates.enter_seat)
    await message.answer("Введите номер места:")


@router.message(BookingStates.enter_seat)
async def enter_seat(message: Message, state: FSMContext, service: CinemaService) -> None:
    try:
        seat = int(message.text or "")
        if seat <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Место должно быть положительным целым числом. Повторите ввод.")
        return
    await state.update_data(seat=seat)
    data = await state.get_data()
    try:
        screening = next(s for s in service.schedule() if s["id"] == data["screening_id"])
    except StopIteration:
        await state.clear()
        await message.answer("Сеанс не найден. Начните бронирование заново.")
        return
    await state.set_state(BookingStates.confirm)
    await message.answer(
        f"Подтвердите бронирование: {screening['title']}, {screening['starts_at']}, "
        f"зал {screening['hall']}, ряд {data['row']}, место {seat}, цена {screening['price']:.0f} ₽.\n"
        "Введите ДА для подтверждения или НЕТ для отмены."
    )


@router.message(BookingStates.confirm)
async def confirm_booking(message: Message, state: FSMContext, service: CinemaService) -> None:
    answer = (message.text or "").strip().lower()
    data = await state.get_data()
    if answer in {"нет", "н", "no"}:
        await state.clear()
        await message.answer("Бронирование отменено.")
        return
    if answer not in {"да", "д", "yes", "y"}:
        await message.answer("Введите «ДА» для подтверждения или «НЕТ» для отмены.")
        return
    try:
        ticket_id = service.book(data["screening_id"], data["row"], data["seat"], data["user_id"])
    except ValueError as exc:
        await state.clear()
        await message.answer(f"Не удалось забронировать билет: {exc}")
        return
    await state.clear()
    await message.answer(f"Билет забронирован. Номер билета: {ticket_id}.")
