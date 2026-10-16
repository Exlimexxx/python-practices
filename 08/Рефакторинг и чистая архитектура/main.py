from models.enums import TicketType
from repositories.memory_repository import InMemoryRepository
from services.cinema_service import CinemaService
from strategies.pricing_strategies import (
    WeekdayStrategy,
    WeekendStrategy,
    SpecialTariffStrategy,
)
from commands.cinema_commands import BuyTicketCommand, RefundTicketCommand


def main():
    # 1. Инициализация репозиториев и сервиса
    session_repo = InMemoryRepository()
    ticket_repo = InMemoryRepository()
    cinema_service = CinemaService(session_repo, ticket_repo)

    # 2. Создание сеанса
    cinema_service.create_session(
        session_id=101, movie_title="Интерстеллар", base_price=400.0
    )

    print("=== 1. Продажа билетов с использованием Factory и Strategy ===")

    # Покупка обычного билета в будний день
    cmd1 = BuyTicketCommand(
        cinema_service, 101, TicketType.STANDARD, WeekdayStrategy()
    )
    cmd1.execute()

    # Покупка VIP-билета в выходной день (400 * 1.3 + 200 = 720.0)
    cmd2 = BuyTicketCommand(
        cinema_service, 101, TicketType.VIP, WeekendStrategy()
    )
    cmd2.execute()

    # Покупка студенческого билета по спецтарифу (400 * 0.7 * 0.5 = 140.0)
    cmd3 = BuyTicketCommand(
        cinema_service, 101, TicketType.STUDENT, SpecialTariffStrategy()
    )
    cmd3.execute()

    print("\n=== 2. Демонстрация работы паттерна Command и отмены (Undo) ===")
    # Отменяем последнюю покупку студенческого билета
    cmd3.undo()

    # Возврат VIP-билета через отдельную команду
    refund_cmd = RefundTicketCommand(cinema_service, ticket_id=2)
    refund_cmd.execute()


if __name__ == "__main__":
    main()