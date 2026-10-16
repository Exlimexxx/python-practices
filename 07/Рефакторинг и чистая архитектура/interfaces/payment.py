from typing import Protocol


class PaymentMethod(Protocol):
    """OCP & ISP: Интерфейс стратегии оплаты."""

    def process_payment(self, amount: float) -> bool:
        ...