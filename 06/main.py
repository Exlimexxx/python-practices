import sys
from models import Movie, Hall, Session, SessionStatus, CinemaError
from services import CinemaService, inspect_object
from context import SessionTransactionContext
from protocols import generate_single_report, Reportable
from decorators import repeat


def seed_data(service: CinemaService) -> None:
    """Заполнение начальными демонстрационными данными."""
    m1 = Movie(id=1, name="Дюна 2", duration_minutes=166, genre="Фантастика", ticket_price=450.0)
    m2 = Movie(id=2, name="Майор Гром", duration_minutes=140, genre="Боевик", ticket_price=350.0)
    m3 = Movie(id=3, name="Головоломка 2", duration_minutes=96, genre="Мультфильм", ticket_price=300.0)

    h1 = Hall(id=1, name="Зал 1 (Запад)", capacity=50, is_vip=False)
    h2 = Hall(id=2, name="Зал VIP 2", capacity=15, is_vip=True)

    for m in (m1, m2, m3):
        service.add_movie(m)
    for h in (h1, h2):
        service.add_hall(h)

    s1 = Session(id=101, name="Утренний сеанс", movie=m1, hall=h1, sold_tickets=40, status=SessionStatus.SCHEDULED)
    s2 = Session(id=102, name="Дневной VIP", movie=m2, hall=h2, sold_tickets=15, status=SessionStatus.COMPLETED)
    s3 = Session(id=103, name="Вечерний сеанс", movie=m3, hall=h1, sold_tickets=10, status=SessionStatus.SCHEDULED)

    service.add_session(s1)
    service.add_session(s2)
    service.add_session(s3)


@repeat(count=2)
def demo_decorated_function(text: str) -> str:
    """Функция для демонстрации декоратора с параметром @repeat."""
    print(f"    [ДЕМО-ФУНКЦИЯ] Выполнение: {text}")
    return f"Успех: {text}"


def print_menu() -> None:
    print("\n" + "=" * 45)
    print("      СИСТЕМА УПРАВЛЕНИЯ КИНОТЕАТРОМ")
    print("=" * 45)
    print("1. Добавить сеанс")
    print("2. Удалить сеанс")
    print("3. Найти сеанс по ID")
    print("4. Вывести все сеансы")
    print("5. Изменить статус сеанса")
    print("6. Выполнить продажу билетов")
    print("7. Топ популярных фильмов")
    print("8. Получить статистику")
    print("9. Интроспекция объекта")
    print("10. Демонстрация Protocol")
    print("11. Демонстрация Декораторов")
    print("12. Демонстрация Контекстного Менеджера")
    print("0. Выход")
    print("=" * 45)


def main() -> None:
    service = CinemaService()
    seed_data(service)

    while True:
        print_menu()
        choice = input("Выберите пункт меню: ").strip()

        try:
            if choice == "1":
                sid = int(input("Введите ID сеанса: "))
                name = input("Введите название сеанса: ")
                print("Доступные фильмы:", [f"{m.id}: {m.name}" for m in service.movies.values()])
                mid = int(input("ID фильма: "))
                print("Доступные залы:", [f"{h.id}: {h.name}" for h in service.halls.values()])
                hid = int(input("ID зала: "))

                movie = service.movies.get(mid)
                hall = service.halls.get(hid)
                if not movie or not hall:
                    print("Ошибка: Выбран несуществующий фильм или зал.")
                    continue

                session = Session(id=sid, name=name, movie=movie, hall=hall)
                service.add_session(session)
                print(f"Сеанс #{sid} успешно добавлен.")

            elif choice == "2":
                sid = int(input("Введите ID сеанса для удаления: "))
                removed = service.remove_session(sid)
                print(f"Удален сеанс: {removed.name}")

            elif choice == "3":
                sid = int(input("Введите ID сеанса: "))
                session = service.get_session(sid)
                print("\nНайдено:")
                print(session.get_report_data())

            elif choice == "4":
                print("\n--- СПИСОК ВСЕХ СЕАНСОВ ---")
                if not service.sessions:
                    print("Сеансы отсутствуют.")
                for s in service.sessions.values():
                    print(s.get_report_data())

            elif choice == "5":
                sid = int(input("Введите ID сеанса: "))
                session = service.get_session(sid)
                print("Статусы: 1-Запланирован, 2-Идёт, 3-Завершён, 4-Отменён")
                st_choice = input("Выберите новый статус: ").strip()
                status_map = {
                    "1": SessionStatus.SCHEDULED,
                    "2": SessionStatus.IN_PROGRESS,
                    "3": SessionStatus.COMPLETED,
                    "4": SessionStatus.CANCELLED
                }
                new_status = status_map.get(st_choice)
                if not new_status:
                    print("Некорректный выбор статуса.")
                    continue
                session.change_status(new_status)
                print(f"Статус сеанса #{sid} изменен на '{new_status.value}'.")

            elif choice == "6":
                sid = int(input("Введите ID сеанса: "))
                count = int(input("Количество билетов для продажи: "))
                service.sell_tickets(sid, count)
                occ = service.calculate_hall_occupancy(sid)
                print(f"Успешно продано {count} билетов. Загрузка зала: {occ:.1f}%")

            elif choice == "7":
                print("\n--- ТОП ПОПУЛЯРНЫХ ФИЛЬМОВ ---")
                popular = service.get_popular_movies()
                for rank, (m_name, tickets) in enumerate(popular, start=1):
                    print(f"{rank}. {m_name} — проданных билетов: {tickets}")

            elif choice == "8":
                print("\n--- ИТОГОВАЯ СТАТИСТИКА ---")
                stats = service.get_statistics()
                for key, val in stats.items():
                    print(f"  • {key}: {val}")

            elif choice == "9":
                sid = int(input("Введите ID сеанса для интроспекции: "))
                session = service.get_session(sid)
                print(inspect_object(session))

            elif choice == "10":
                print("\n--- ДЕМОНСТРАЦИЯ PROTOCOL (Reportable) ---")
                print("Передача разных объектов (Movie, Hall, Session) в единый метод:")
                sample_movie = list(service.movies.values())[0]
                sample_hall = list(service.halls.values())[0]
                sample_session = list(service.sessions.values())[0]

                for obj in (sample_movie, sample_hall, sample_session):
                    if isinstance(obj, Reportable):
                        print(generate_single_report(obj))

            elif choice == "11":
                print("\n--- ДЕМОНСТРАЦИЯ ДЕКОРАТОРОВ ---")
                demo_decorated_function("Тестовый запуск")

            elif choice == "12":
                print("\n--- ДЕМОНСТРАЦИЯ КОНТЕКСТНОГО МЕНЕДЖЕРА ---")
                sid = int(input("Введите ID сеанса: "))
                session = service.get_session(sid)

                print("\n1. Успешная транзакция:")
                with SessionTransactionContext(session) as s:
                    s.sold_tickets += 2
                    print(f"    [Внутри контекста]: Продано мест теперь: {s.sold_tickets}")

                print("\n2. Откат транзакции при ошибке:")
                with SessionTransactionContext(session) as s:
                    s.sold_tickets += 1000  # Намеренно некорректное значение
                    raise ValueError("Искусственная ошибка внутри блока с менеджером!")

                print(f"    [После отката]: Продано мест осталось: {session.sold_tickets}")

            elif choice == "0":
                print("Завершение работы программы.")
                sys.exit(0)

            else:
                print("Неверный ввод, попробуйте снова.")

        except ValueError as e:
            print(f"[ОШИБКА ВВОДА]: Введены некорректные данные ({e})")
        except CinemaError as e:
            print(f"[ОШИБКА ПРЕДМЕТНОЙ ОБЛАСТИ]: {e}")
        except Exception as e:
            print(f"[НЕПРЕДВИДЕННАЯ ОШИБКА]: {e}")


if __name__ == "__main__":
    main()