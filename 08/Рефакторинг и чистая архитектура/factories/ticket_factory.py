from models.entities import Ticket, Session
from models.enums import TicketType
from interfaces.strategies import PricingStrategy


class TicketFactory:
    """Паттерн Factory: Отвечает за создание объектов билетов разных типов."""

    @staticmethod
    def create_ticket(
        ticket_id: int,
        session: Session,
        ticket_type: TicketType,
        pricing_strategy: PricingStrategy,
    ) -> Ticket:

        # 1. Применяем выбранную стратегию дня
        calculated_price = pricing_strategy.calculate_price(session.base_price)

        # 2. Применяем особенности типа билета
        if ticket_type == TicketType.STANDARD:
            final_price = calculated_price
        elif ticket_type == TicketType.VIP:
            final_price = calculated_price + 200.0  # Наценка за VIP-ложу
        elif ticket_type == TicketType.STUDENT:
            final_price = calculated_price * 0.5  # Студенческая скидка 50%
        else:
            raise ValueError(f"Неизвестный тип билета: {ticket_type}")

        return Ticket(
            ticket_id=ticket_id,
            session_id=session.session_id,
            ticket_type=ticket_type,
            price=round(final_price, 2),
        )