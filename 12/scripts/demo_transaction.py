"""Демонстрация транзакций: успешное бронирование и откат при ошибке.

Запуск:
    python scripts/demo_transaction.py
"""
from __future__ import annotations

import logging
import os
import sys
from datetime import date

# Делаем пакет app импортируемым при запуске скрипта из любого каталога.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import configure_database, drop_db, get_session_factory, init_db
from app.exceptions import (
    BookingConflictError,
    NotEnoughCapacityError,
    NotFoundError,
    ValidationError,
)
from app.repositories.booking_repository import BookingRepository
from app.services.hotel_service import HotelService

DB_URL = "sqlite:///demo/transaction_demo.db"


def header(text: str) -> None:
    """Печать заголовка раздела."""
    print()
    print("=" * 74)
    print(text)
    print("=" * 74)


def main() -> int:
    # SQL-эхо выводим в stdout, чтобы оно попало в сохранённый протокол.
    logging.basicConfig(
        level=logging.INFO,
        format="SQL> %(message)s",
        stream=sys.stdout,
        force=True,
    )
    configure_database(DB_URL)
    # Включаем SQL-эхо вручную, чтобы записи шли в наш stdout-обработчик.
    logging.getLogger("sqlalchemy.engine.Engine").setLevel(logging.INFO)
    drop_db()
    init_db()

    session = get_session_factory()()
    service = HotelService(session)
    repo = BookingRepository(session)

    print("База данных:", DB_URL)
    guest = service.register_guest("Иванов Иван Иванович", "ivanov@example.com", "+7-900-111-22-33")
    room = service.add_room("101", "Стандарт", 2, "3000")
    print("Подготовлено:", guest, "|", room)

    # ---------------------------------------------------------------- успех
    header("ТРАНЗАКЦИЯ 1. Успешное бронирование 2025-06-01..2025-06-05 (шаги: проверки → INSERT → COMMIT)")
    before = repo.count()
    result = service.book_room(guest.id, room.id, date(2025, 6, 1), date(2025, 6, 5), guests_count=2)
    print("РЕЗУЛЬТАТ:", result.describe())
    print(f"Строк в bookings: было {before}, стало {repo.count()} (транзакция зафиксирована)")

    # Проверяем, что данные реально зафиксированы — читаем в НОВОЙ сессии.
    other = get_session_factory()()
    try:
        fresh = BookingRepository(other)
        print(f"Проверка в новой сессии: броней = {fresh.count()}, первая = {fresh.get_by_id(result.booking.id)}")
    finally:
        other.close()

    # -------------------------------------------------------------- откат 1
    header("ТРАНЗАКЦИЯ 2. ОТКАТ: пересечение дат (2025-06-03..2025-06-07)")
    before = repo.count()
    try:
        service.book_room(guest.id, room.id, date(2025, 6, 3), date(2025, 6, 7), guests_count=1)
    except BookingConflictError as exc:
        print("Перехвачено исключение BookingConflictError:", exc)
    after = repo.count()
    print(f"Строк в bookings: было {before}, стало {after} — выполнен session.rollback(), запись не создана")

    # -------------------------------------------------------------- откат 2
    header("ТРАНЗАКЦИЯ 3. ОТКАТ: превышение вместимости (мест 2, запрошено 4)")
    before = repo.count()
    try:
        service.book_room(guest.id, room.id, date(2025, 6, 10), date(2025, 6, 12), guests_count=4)
    except NotEnoughCapacityError as exc:
        print("Перехвачено исключение NotEnoughCapacityError:", exc)
    print(f"Строк в bookings: было {before}, стало {repo.count()} — откат выполнен")

    # -------------------------------------------------------------- откат 3
    header("ТРАНЗАКЦИЯ 4. ОТКАТ: некорректные даты (выезд раньше заезда)")
    before = repo.count()
    try:
        service.book_room(guest.id, room.id, date(2025, 6, 12), date(2025, 6, 10), guests_count=1)
    except ValidationError as exc:
        print("Перехвачено исключение ValidationError:", exc)
    print(f"Строк в bookings: было {before}, стало {repo.count()} — откат выполнен")

    # -------------------------------------------------------------- откат 4
    header("ТРАНЗАКЦИЯ 5. ОТКАТ: несуществующий гость (guest_id=999, нарушение FK)")
    before = repo.count()
    try:
        service.book_room(999, room.id, date(2025, 6, 10), date(2025, 6, 12), guests_count=1)
    except NotFoundError as exc:
        print("Перехвачено исключение NotFoundError:", exc)
    print(f"Строк в bookings: было {before}, стало {repo.count()} — откат выполнен")

    # ---------------------------------------------------------------- итог
    header("ИТОГ")
    print("Все брони в базе:")
    for booking in repo.list_all():
        print("  ", booking, "| отель:", booking.room, "| гость:", booking.guest.full_name)
    print("Сессия после серии откатов работоспособна, всего броней:", repo.count())

    session.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
