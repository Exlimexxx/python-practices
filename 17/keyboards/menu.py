"""Клавиатуры Telegram-интерфейса."""
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Фильмы"), KeyboardButton(text="Расписание")],
            [KeyboardButton(text="Найти фильм"), KeyboardButton(text="Забронировать билет")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите раздел кинотеатра",
    )


def movie_buttons(movies: list[dict]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{m['title']} ({m['rating']:.1f})", callback_data=f"movie:{m['id']}")]
        for m in movies[:10]
    ])


def screening_buttons(screenings: list[dict]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"#{s['id']} {s['title']} — {s['starts_at']} ({s['price']:.0f} ₽)",
            callback_data=f"booking:{s['id']}",
        )]
        for s in screenings[:10]
    ])
