from typing import List, Optional
from models.entities import Session, Ticket
from models.enums import TicketType
from interfaces.repository import Repository
from interfaces.strategies import PricingStrategy
from factories.ticket_factory import TicketFactory


class CinemaService:

    def __init__(
        self,
        session_repo: Repository[Session],
        ticket_repo: Repository[Ticket],
    ) -> None:
        self.session_repo = session_repo
        self.ticket_repo = ticket_repo
        self._ticket_id_counter = 1

    def create_session(
        self, session_id: int, movie_title: str, base_price: float
    ) -> Session:
        session = Session(
            session_id=session_id,
            movie_title=movie_title,
            base_price=base_price,
        )
        self.session_repo.add(session)
        return session

    def sell_ticket(
        self,
        session_id: int,
        ticket_type: TicketType,
        pricing_strategy: PricingStrategy,
    ) -> Ticket:
        session = self.session_repo.get_by_id(session_id)
        if not session:
            raise ValueError(f"Сеанс №{session_id} не найден.")

        ticket = TicketFactory.create_ticket(
            ticket_id=self._ticket_id_counter,
            session=session,
            ticket_type=ticket_type,
            pricing_strategy=pricing_strategy,
        )
        self._ticket_id_counter += 1
        self.ticket_repo.add(ticket)
        return ticket

    def refund_ticket(self, ticket_id: int) -> bool:
        ticket = self.ticket_repo.get_by_id(ticket_id)
        if ticket and ticket.is_active:
            ticket.is_active = False
            self.ticket_repo.add(ticket)
            return True
        return False