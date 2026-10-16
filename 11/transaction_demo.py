"""Демонстрация транзакции продажи билетов: успешный COMMIT и ROLLBACK.

Запуск:  python transaction_demo.py [--db cinema.db]
"""
from __future__ import annotations

import argparse
import logging
import sys

from cache import create_cache
from db import DB_PATH, connect, fetch_one
from repository import ScreeningRepository
from service import CinemaService, SeatUnavailableError

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(name)s: %(message)s",
                    stream=sys.stdout)
logger = logging.getLogger("demo.transaction")


def show_state(conn, screening_id: int) -> tuple[int, int]:
    """Возвращает (tickets_sold, число записей о продажах)."""
    row = fetch_one(conn, "SELECT tickets_sold FROM screenings WHERE id = ?", (screening_id,))
    sales = fetch_one(conn, "SELECT COUNT(*) AS cnt FROM ticket_sales WHERE screening_id = ?",
                      (screening_id,))
    tickets_sold = int(row["tickets_sold"]) if row else -1
    sales_count = int(sales["cnt"]) if sales else -1
    return tickets_sold, sales_count


def main() -> int:
    parser = argparse.ArgumentParser(description="Демонстрация транзакции продажи билетов")
    parser.add_argument("--db", default=str(DB_PATH))
    args = parser.parse_args()

    conn = connect(args.db)
    service = CinemaService(conn, create_cache())
    screenings = ScreeningRepository(conn)

    screening_id = 5   # сеанс фильма «Форрест Гамп», Зал 3 «VIP» (30 мест)
    conn.execute("DELETE FROM ticket_sales")
    conn.execute("UPDATE screenings SET tickets_sold = 0 WHERE id = ?", (screening_id,))

    print("=" * 78)
    print("ДЕМОНСТРАЦИЯ ТРАНЗАКЦИЙ (продажа билетов)")
    print("=" * 78)

    seats = screenings.seats_left(screening_id)
    sold, sales = show_state(conn, screening_id)
    print(f"Сеанс id={screening_id}, свободных мест: {seats}, "
          f"продано билетов: {sold}, записей в ticket_sales: {sales}")

    # ---------- 1. Успешная транзакция: COMMIT --------------------------
    print()
    print("-" * 78)
    print("СЛУЧАЙ 1. Успешная продажа 3 билетов -> COMMIT")
    print("-" * 78)
    try:
        sale = service.sell_ticket(screening_id, tickets=3)
        print(f"  OK  продажа #{sale.sale_id}: «{sale.movie_title}», "
              f"{sale.tickets} бил., итого {sale.total_price:.2f} руб., "
              f"осталось мест: {sale.seats_left}")
    except Exception as exc:  # noqa: BLE001 - для наглядности демонстрации
        print(f"  ОШИБКА: {exc}")

    sold, sales = show_state(conn, screening_id)
    print(f"  Состояние БД после COMMIT: tickets_sold={sold}, записей о продажах={sales}")

    # ---------- 2. Откат: ROLLBACK --------------------------------------
    print()
    print("-" * 78)
    print("СЛУЧАЙ 2. Попытка продать 100 билетов при 27 свободных местах -> ROLLBACK")
    print("-" * 78)
    sold_before, sales_before = show_state(conn, screening_id)
    try:
        service.sell_ticket(screening_id, tickets=100)
        print("  ОШИБКА ДЕМОНСТРАЦИИ: исключения не было (так быть не должно)")
    except SeatUnavailableError as exc:
        print(f"  Ожидаемое исключение SeatUnavailableError: {exc}")
        print("  Транзакция откатана: ROLLBACK")

    sold_after, sales_after = show_state(conn, screening_id)
    print(f"  Состояние БД после ROLLBACK: tickets_sold={sold_after}, "
          f"записей о продажах={sales_after}")
    if (sold_before, sales_before) == (sold_after, sales_after):
        print("  Проверка пройдена: данные не изменились, откат сработал.")
    else:
        print("  ПРОВЕРКА НЕ ПРОЙДЕНА: данные изменились!")

    # ---------- 3. Продолжение после отката -----------------------------
    print()
    print("-" * 78)
    print("СЛУЧАЙ 3. Успешная продажа 2 билетов после отката -> COMMIT")
    print("-" * 78)
    sale = service.sell_ticket(screening_id, tickets=2)
    print(f"  OK  продажа #{sale.sale_id}: {sale.tickets} бил., "
          f"итого {sale.total_price:.2f} руб., осталось мест: {sale.seats_left}")
    sold, sales = show_state(conn, screening_id)
    print(f"  Итог: tickets_sold={sold}, записей о продажах={sales}")

    print()
    print("=" * 78)
    print("Оба сценария продемонстрированы: COMMIT при успехе, ROLLBACK при ошибке.")
    print("=" * 78)
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
