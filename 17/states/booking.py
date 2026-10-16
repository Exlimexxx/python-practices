"""Четырёхэтапный сценарий бронирования места."""
from aiogram.fsm.state import State, StatesGroup


class BookingStates(StatesGroup):
    choose_screening = State()
    enter_row = State()
    enter_seat = State()
    confirm = State()
