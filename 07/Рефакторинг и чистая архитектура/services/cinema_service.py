from typing import List, Optional
from interfaces.repository import Repository
from interfaces.payment import PaymentMethod
from interfaces.notifier import Notifier
from interfaces.report import ReportGenerator
from models.entities import Session, Ticket, Movie, Hall
from models.enums import TicketStatus


class CinemaService:
    """DIP: Сервис зависит только от абстракций.

    SRP: Отвечает исключительно за проведение бизнес-операций кинотеатра.
    """

    def __init__(

        self,
        session_repo: Repository[Session],
        ticket_repo: Repository[Ticket],
        notifier: Notifier,
        report_generator: ReportGenerator,
    ) -> None:
        # Constructor Injection
        self.session_repo = session_repo
        self.ticket_repo = ticket_repo
        self.notifier = notifier
        self.report_generator = report_generator

    def create_session(
        self,
        session_id: int,
        movie: Movie,
        hall: Hall,
        start_time: str,
        base_price: float,
    ) -> Session:
        session = Session(
            session_id=session_id,
            movie=movie,
            hall=hall,
            start_time=start_time,
            base_price=base_price,
        )
        self.session_repo.add(session)
        self.notifier.notify(
            f"Создан новый сеанс: '{movie.title}' в {start_time}"
        )
        return session

    def sell_ticket(
        self,
        ticket_id: int,
        session_id: int,
        seat_number: int,
        payment_method: PaymentMethod,
        is_refundable: bool = True,
    ) -> Optional[Ticket]:
        session = self.session_repo.get_by_id(session_id)
        if not session:
            raise ValueError(f"Сеанс с ID {session_id} не найден.")

        price = session.calculate_ticket_price() if is_refundable else 0.0

        # OCP: Вызов внешнего способа оплаты без знания его деталей
        if price > 0 and not payment_method.process_payment(price):
            self.notifier.notify(
                f"Ошибка оплаты билета #{ticket_id}. Операция отменена."
            )
            return None

        ticket = Ticket(
            ticket_id=ticket_id,
            session=session,
            seat_number=seat_number,
            price=price,
            is_refundable=is_refundable,
        )
        self.ticket_repo.add(ticket)
        self.notifier.notify(
            f"Билет #{ticket_id} на фильм '{session.movie.title}' выкуплен."
        )
        return ticket

    def refund_ticket(self, ticket_id: int) -> bool:
        ticket = self.ticket_repo.get_by_id(ticket_id)
        if not ticket:
            raise ValueError(f"Билет #{ticket_id} не найден.")

        # LSP-compliant корректная обработка правил без вылета исключений
        if not ticket.is_refundable:
            self.notifier.notify(
                f"Отказ: Билет #{ticket_id} является невозвратным (акционный/VIP-приглашение)."
            )
            return False

        if ticket.status == TicketStatus.REFUNDED:
            self.notifier.notify(f"Билет #{ticket_id} уже был возвращен ранее.")
            return False

        ticket.status = TicketStatus.REFUNDED
        self.notifier.notify(
            f"Успешный возврат билета #{ticket_id}. Возвращено: {ticket.price:.2f} руб."
        )
        return True

    def get_financial_report(self) -> str:
        tickets = self.ticket_repo.get_all()
        return self.report_generator.generate(tickets)