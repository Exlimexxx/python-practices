from typing import List
from interfaces.report import ReportGenerator
from models.entities import Ticket
from models.enums import TicketStatus


class FinancialTextReportGenerator(ReportGenerator):

    def generate(self, tickets: List[Ticket]) -> str:
        total_sales = sum(
            t.price for t in tickets if t.status == TicketStatus.ACTIVE
        )
        refunded_count = sum(
            1 for t in tickets if t.status == TicketStatus.REFUNDED
        )

        lines = [
            "=== ФИНАНСОВЫЙ ОТЧЕТ КИНОТЕАТРА ===",
            f"Всего проданных/активных билетов: {len(tickets) - refunded_count}",
            f"Количество возвратов: {refunded_count}",
            f"Итоговая выручка: {total_sales:.2f} руб.",
            "==================================",
        ]
        return "\n".join(lines)