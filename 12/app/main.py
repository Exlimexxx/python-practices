"""Консольное приложение «Отель» (лабораторная работа №12, вариант 4).

Запуск:
    python -m app.main
или
    python app/main.py
"""
from __future__ import annotations

import logging
import sys
from datetime import date
from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import Session

from app.database import configure_database, get_database_url, get_session_factory, init_db
from app.exceptions import HotelError
from app.models.booking import BookingStatus
from app.services.hotel_service import HotelService

logger = logging.getLogger("hotel.console")

MENU = """
======================= ОТЕЛЬ: ГЛАВНОЕ МЕНЮ =======================
  1  — Список всех гостей
  2  — Добавить гостя
  3  — Список всех номеров
  4  — Добавить номер
  5  — Забронировать номер (транзакция)
  6  — Отменить бронь
  7  — Брони гостя
  8  — Брони номера
  9  — Свободные номера на даты
 10  — Фильтр номеров (тип/вместимость/цена)
 11  — Сортировка номеров (по цене / по вместимости)
 12  — Сортировка броней (по дате заезда / по стоимости)
 13  — Поиск гостей по атрибутам
 14  — Изменить цену номера
 15  — Изменить статус брони
 16  — Удалить бронь
 17  — Удалить гостя
 18  — Удалить номер
  0  — Выход
==================================================================="""


class ConsoleApp:
    """Интерактивный интерфейс поверх HotelService."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.service = HotelService(session)

    # ------------------------------------------------------------ ввод данных
    @staticmethod
    def ask(prompt: str) -> str:
        """Прочитать строку и продублировать её в выводе (для протокола)."""
        value = input(prompt + " ")
        print(value)
        return value.strip()

    @staticmethod
    def ask_int(prompt: str, *, required: bool = True, default: int | None = None) -> int | None:
        """Прочитать целое число; при ошибке вернуть default или None."""
        raw = ConsoleApp.ask(prompt)
        if not raw:
            if required:
                raise HotelError("Значение обязательно для заполнения")
            return default
        try:
            return int(raw)
        except ValueError as exc:
            raise HotelError(f"Ожидалось целое число, получено {raw!r}") from exc

    @staticmethod
    def ask_decimal(prompt: str, *, required: bool = True) -> Decimal | None:
        """Прочитать десятичное число (цену)."""
        raw = ConsoleApp.ask(prompt)
        if not raw:
            if required:
                raise HotelError("Значение обязательно для заполнения")
            return None
        try:
            return Decimal(raw)
        except InvalidOperation as exc:
            raise HotelError(f"Ожидалось число, получено {raw!r}") from exc

    @staticmethod
    def ask_date(prompt: str) -> date:
        """Прочитать дату в формате ГГГГ-ММ-ДД."""
        raw = ConsoleApp.ask(prompt)
        try:
            return date.fromisoformat(raw)
        except ValueError as exc:
            raise HotelError(f"Некорректная дата {raw!r}; формат ГГГГ-ММ-ДД") from exc

    @staticmethod
    def ask_yes_no(prompt: str, default: bool = True) -> bool:
        """Прочитать подтверждение да/нет."""
        raw = ConsoleApp.ask(prompt)
        if not raw:
            return default
        return raw[0].lower() in {"y", "д", "1"}

    # -------------------------------------------------------------- отрисовка
    @staticmethod
    def show(title: str, rows: list[str]) -> None:
        """Вывести раздел со списком строк."""
        print(f"--- {title} ---")
        if not rows:
            print("  (пусто)")
        for row in rows:
            print("  " + row)

    # ---------------------------------------------------------------- действия
    def action_list_guests(self) -> None:
        self.show("ГОСТИ", [str(g) for g in self.service.list_guests()])

    def action_add_guest(self) -> None:
        full_name = self.ask("ФИО гостя:")
        email = self.ask("Email:")
        phone = self.ask("Телефон:")
        guest = self.service.register_guest(full_name, email, phone)
        print(f"OK: добавлен {guest}")

    def action_list_rooms(self) -> None:
        self.show("НОМЕРА", [str(r) for r in self.service.list_rooms()])

    def action_add_room(self) -> None:
        number = self.ask("Номер комнаты:")
        room_type = self.ask("Тип номера:")
        capacity = self.ask_int("Вместимость (мест):")
        price = self.ask_decimal("Цена за ночь:")
        room = self.service.add_room(number, room_type, int(capacity or 1), price or Decimal("0"))
        print(f"OK: добавлен {room}")

    def action_book(self) -> None:
        guest_id = self.ask_int("ID гостя:")
        room_id = self.ask_int("ID номера:")
        check_in = self.ask_date("Дата заезда (ГГГГ-ММ-ДД):")
        check_out = self.ask_date("Дата выезда (ГГГГ-ММ-ДД):")
        guests_count = self.ask_int("Количество гостей:", required=False, default=1)
        result = self.service.book_room(
            int(guest_id or 0), int(room_id or 0), check_in, check_out, int(guests_count or 1)
        )
        print("OK: " + result.describe())

    def action_cancel_booking(self) -> None:
        booking_id = self.ask_int("ID брони:")
        booking = self.service.cancel_booking(int(booking_id or 0))
        print(f"OK: {booking}")

    def action_bookings_of_guest(self) -> None:
        guest_id = self.ask_int("ID гостя:")
        rows = [str(b) for b in self.service.bookings_of_guest(int(guest_id or 0))]
        self.show(f"БРОНИ ГОСТЯ #{guest_id}", rows)

    def action_bookings_of_room(self) -> None:
        room_id = self.ask_int("ID номера:")
        rows = [str(b) for b in self.service.bookings_of_room(int(room_id or 0))]
        self.show(f"БРОНИ НОМЕРА #{room_id}", rows)

    def action_available_rooms(self) -> None:
        check_in = self.ask_date("Дата заезда:")
        check_out = self.ask_date("Дата выезда:")
        min_capacity = self.ask_int("Мин. вместимость (Enter — не важно):", required=False)
        rooms = self.service.available_rooms(check_in, check_out, min_capacity)
        self.show(f"СВОБОДНЫЕ НОМЕРА {check_in}..{check_out}", [str(r) for r in rooms])

    def action_filter_rooms(self) -> None:
        room_type = self.ask("Тип номера (Enter — любой):") or None
        min_capacity = self.ask_int("Мин. вместимость (Enter — не важно):", required=False)
        min_price = self.ask_decimal("Цена от (Enter — не важно):", required=False)
        max_price = self.ask_decimal("Цена до (Enter — не важно):", required=False)
        rooms = self.service.filter_rooms(room_type, min_capacity, True, min_price, max_price)
        self.show("РЕЗУЛЬТАТ ФИЛЬТРАЦИИ", [str(r) for r in rooms])

    def action_sort_rooms(self) -> None:
        key = self.ask("Ключ сортировки (price/capacity):").lower()
        direction = self.ask("Направление (asc/desc):").lower() or "asc"
        descending = direction.startswith("desc")
        if key.startswith("cap"):
            rooms = self.service.rooms_sorted_by_capacity(descending)
        else:
            rooms = self.service.rooms_sorted_by_price(descending)
        self.show("СОРТИРОВКА НОМЕРОВ", [str(r) for r in rooms])

    def action_sort_bookings(self) -> None:
        key = self.ask("Ключ сортировки (date/price):").lower()
        direction = self.ask("Направление (asc/desc):").lower() or "asc"
        descending = direction.startswith("desc")
        if key.startswith("p"):
            bookings = self.service.bookings_sorted_by_total(descending)
        else:
            bookings = self.service.bookings_sorted_by_check_in(descending)
        self.show("СОРТИРОВКА БРОНЕЙ", [str(b) for b in bookings])

    def action_search_guests(self) -> None:
        full_name = self.ask("Часть ФИО (Enter — не важно):") or None
        phone = self.ask("Часть телефона (Enter — не важно):") or None
        email = self.ask("Часть email (Enter — не важно):") or None
        guests = self.service.search_guests(full_name, phone, email)
        self.show("НАЙДЕННЫЕ ГОСТИ", [str(g) for g in guests])

    def action_update_room_price(self) -> None:
        room_id = self.ask_int("ID номера:")
        new_price = self.ask_decimal("Новая цена за ночь:")
        room = self.service.update_room(int(room_id or 0), price_per_night=new_price)
        print(f"OK: {room}")

    def action_change_status(self) -> None:
        booking_id = self.ask_int("ID брони:")
        status = self.ask(f"Новый статус ({'/'.join(s.value for s in BookingStatus)}):")
        booking = self.service.change_booking_status(int(booking_id or 0), status)
        print(f"OK: {booking}")

    def action_delete_booking(self) -> None:
        booking_id = self.ask_int("ID брони:")
        self.service.delete_booking(int(booking_id or 0))
        print(f"OK: бронь #{booking_id} удалена")

    def action_delete_guest(self) -> None:
        guest_id = self.ask_int("ID гостя:")
        self.service.delete_guest(int(guest_id or 0))
        print(f"OK: гость #{guest_id} удалён")

    def action_delete_room(self) -> None:
        room_id = self.ask_int("ID номера:")
        self.service.delete_room(int(room_id or 0))
        print(f"OK: номер #{room_id} удалён")

    # -------------------------------------------------------------------- меню
    HANDLERS = {
        "1": action_list_guests,
        "2": action_add_guest,
        "3": action_list_rooms,
        "4": action_add_room,
        "5": action_book,
        "6": action_cancel_booking,
        "7": action_bookings_of_guest,
        "8": action_bookings_of_room,
        "9": action_available_rooms,
        "10": action_filter_rooms,
        "11": action_sort_rooms,
        "12": action_sort_bookings,
        "13": action_search_guests,
        "14": action_update_room_price,
        "15": action_change_status,
        "16": action_delete_booking,
        "17": action_delete_guest,
        "18": action_delete_room,
    }

    def run(self) -> None:
        """Основной цикл меню."""
        print("Приложение «Отель». База данных: " + get_database_url())
        print(MENU)
        print("Подсказка: введите h, чтобы показать меню снова.")
        while True:
            try:
                choice = self.ask("Меню (1-18, 0-выход, h-справка). Ваш выбор:")
            except EOFError:
                print("\nВвод завершён — выход.")
                return
            if choice == "0":
                print("Выход. Всего доброго!")
                return
            if choice in {"h", "м", "menu"}:
                print(MENU)
                continue
            handler = self.HANDLERS.get(choice)
            if handler is None:
                print(f"!! Неизвестный пункт меню: {choice!r}")
                continue
            try:
                handler(self)
            except HotelError as exc:
                # Понятное сообщение вместо аварийного завершения.
                print(f"!! Ошибка: {exc}")
                logger.warning("Пункт меню %s: %s", choice, exc)
            except Exception as exc:  # noqa: BLE001 - приложение не должно падать
                self.session.rollback()
                print(f"!! Непредвиденная ошибка: {exc!r}")
                logger.exception("Необработанная ошибка в пункте меню %s", choice)


def main() -> int:
    """Точка входа: настройка БД и запуск меню."""
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
    )
    configure_database()
    init_db()
    session = get_session_factory()()
    try:
        ConsoleApp(session).run()
    except KeyboardInterrupt:
        print("\nПрервано пользователем.")
    finally:
        session.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
