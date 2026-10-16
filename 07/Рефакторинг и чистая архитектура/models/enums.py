from enum import Enum


class TicketStatus(str, Enum):
    ACTIVE = "Активен"
    REFUNDED = "Возвращен"


class HallType(str, Enum):
    STANDARD = "Стандартный Зал"
    IMAX = "IMAX 3D Зал"
    VIP = "VIP Зал с диванами"