from enum import Enum


class TicketType(str, Enum):
    STANDARD = "standard"
    VIP = "vip"
    STUDENT = "student"


class DayType(str, Enum):
    WEEKDAY = "weekday"
    WEEKEND = "weekend"
    SPECIAL = "special"