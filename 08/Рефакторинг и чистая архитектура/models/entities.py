from dataclasses import dataclass
from models.enums import TicketType


@dataclass
class Session:
    session_id: int
    movie_title: str
    base_price: float


@dataclass
class Ticket:
    ticket_id: int
    session_id: int
    ticket_type: TicketType
    price: float
    is_active: bool = True