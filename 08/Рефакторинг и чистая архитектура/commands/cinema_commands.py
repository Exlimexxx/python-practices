from interfaces.command import Command
from services.cinema_service import CinemaService
from models.enums import TicketType
from interfaces.strategies import PricingStrategy
from models.entities import Ticket


class BuyTicketCommand(Command):
    """Команда для покупки билета с поддержкой отмены (Undo)."""

    def __init__(

        self,
        service: CinemaService,
        session_id: int,
        ticket_type: TicketType,
        pricing_strategy: PricingStrategy,
    ) -> None:
        self.service = service
        self.session_id = session_id
        self.ticket_type = ticket_type
        self.pricing_strategy = pricing_strategy
        self.created_ticket: Optional[Ticket] = None

    def execute(self) -> bool:
        self.created_ticket = self.service.sell_ticket(
            session_id=self.session_id,
            ticket_type=self.ticket_type,
            pricing_strategy=self.pricing_strategy,
        )
        print(
            f"[COMMAND] Продан билет #{self.created_ticket.ticket_id} | Тип: {self.created_ticket.ticket_type.value} | Цена: {self.created_ticket.price} руб."
        )
        return True

    def undo(self) -> None:
        if self.created_ticket:
            self.service.refund_ticket(self.created_ticket.ticket_id)
            print(
                f"[COMMAND UNDO] Операция отменена. Билет #{self.created_ticket.ticket_id} возвращен."
            )


class RefundTicketCommand(Command):
    """Команда возврата билета."""

    def __init__(self, service: CinemaService, ticket_id: int) -> None:
        self.service = service
        self.ticket_id = ticket_id
        self.success = False

    def execute(self) -> bool:
        self.success = self.service.refund_ticket(self.ticket_id)
        if self.success:
            print(f"[COMMAND] Билет #{self.ticket_id} успешно возвращен.")
        return self.success

    def undo(self) -> None:
        ticket = self.service.ticket_repo.get_by_id(self.ticket_id)
        if ticket:
            ticket.is_active = True
            self.service.ticket_repo.add(ticket)
            print(
                f"[COMMAND UNDO] Отмена возврата. Билет #{self.ticket_id} снова активен."
            )