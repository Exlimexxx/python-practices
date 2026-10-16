from typing import Protocol, List
from models.entities import Ticket


class ReportGenerator(Protocol):
    """ISP: Интерфейс для генерации отчетов."""

    def generate(self, tickets: List[Ticket]) -> str:
        ...