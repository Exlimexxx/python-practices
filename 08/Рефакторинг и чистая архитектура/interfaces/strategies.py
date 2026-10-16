from typing import Protocol


class PricingStrategy(Protocol):

    def calculate_price(self, base_price: float) -> float:
        ...