from models.entities import Movie, Hall
from models.enums import HallType
from repositories.memory_repository import InMemoryRepository
from infrastructure.payment_methods import CardPayment, PushkinCardPayment
from infrastructure.notifiers import ConsoleNotifier
from infrastructure.report_generators import FinancialTextReportGenerator
from services.cinema_service import CinemaService
from ui.console_ui import ConsoleUI


def main():
    # 1. Инициализация репозиториев и инфраструктуры (Composition Root)
    session_repository = InMemoryRepository()
    ticket_repository = InMemoryRepository()

    notifier = ConsoleNotifier()
    report_generator = FinancialTextReportGenerator()

    # 2. Внедрение зависимостей (Constructor Injection)
    cinema_service = CinemaService(
        session_repo=session_repository,
        ticket_repo=ticket_repository,
        notifier=notifier,
        report_generator=report_generator,
    )

    ui = ConsoleUI(cinema_service=cinema_service)

    # 3. Подготовка сущностей
    movie1 = Movie(
        movie_id=1, title="Майор Гром: Игра", duration_minutes=150
    )
    movie2 = Movie(movie_id=2, title="Дюна: Часть вторая", duration_minutes=166)

    hall_std = Hall(
        hall_id=1, name="Зал 1", hall_type=HallType.STANDARD, capacity=100
    )
    hall_imax = Hall(
        hall_id=2, name="Зал IMAX", hall_type=HallType.IMAX, capacity=200
    )

    print("--- 1. Создание сеансов ---")
    session1 = cinema_service.create_session(
        session_id=101,
        movie=movie1,
        hall=hall_std,
        start_time="18:00",
        base_price=400.0,
    )
    session2 = cinema_service.create_session(
        session_id=102,
        movie=movie2,
        hall=hall_imax,
        start_time="20:30",
        base_price=500.0,
    )

    print("\n--- 2. Продажа билетов разными способами оплаты (OCP) ---")
    # Оплата банковской картой
    card_payment = CardPayment(card_number="2202-4444-5555-8888")
    cinema_service.sell_ticket(
        ticket_id=1,
        session_id=101,
        seat_number=12,
        payment_method=card_payment,
    )

    # Оплата Пушкинской картой на IMAX (сработает коэффициент цены 1.5)
    pushkin_payment = PushkinCardPayment(card_id="PK-991283")
    cinema_service.sell_ticket(
        ticket_id=2,
        session_id=102,
        seat_number=5,
        payment_method=pushkin_payment,
    )

    # Выдача бесплатного невозвратного пригласительного билета
    cinema_service.sell_ticket(
        ticket_id=3,
        session_id=102,
        seat_number=1,
        payment_method=card_payment,
        is_refundable=False,
    )

    print("\n--- 3. Возврат билетов (LSP) ---")
    # Обычный билет возвращается без проблем
    cinema_service.refund_ticket(ticket_id=1)

    # Попытка вернуть невозвратный билет безопасна (без NotImplementedError)
    cinema_service.refund_ticket(ticket_id=3)

    print("\n--- 4. Формирование отчёта (SRP) ---")
    ui.show_report()


if __name__ == "__main__":
    main()