from dataclasses import dataclass
from models.enums import TicketStatus, HallType


@dataclass
class Movie:
    movie_id: int
    title: str
    duration_minutes: int


@dataclass
class Hall:
    hall_id: int
    name: str
    hall_type: HallType
    capacity: int

    def get_price_multiplier(self) -> float:
        """LSP: Расчет коэффициента цены в зависимости от типа зала."""
        if self.hall_type == HallType.IMAX:
            return 1.5
        elif self.hall_type == HallType.VIP:
            return 2.0
        return 1.0


@dataclass
class Session:
    session_id: int
    movie: Movie
    hall: Hall
    start_time: str
    base_price: float

    def calculate_ticket_price(self) -> float:
        return self.base_price * self.hall.get_price_multiplier()


@dataclass
class Ticket:
    ticket_id: int
    session: Session
    seat_number: int
    price: float
    status: TicketStatus = TicketStatus.ACTIVE
    is_refundable: bool = True