from interfaces.strategies import PricingStrategy


class WeekdayStrategy(PricingStrategy):
    """Стратегия: Будний день (базовая цена)."""

    def calculate_price(self, base_price: float) -> float:
        return base_price


class WeekendStrategy(PricingStrategy):
    """Стратегия: Выходной день (+30% к цене)."""

    def calculate_price(self, base_price: float) -> float:
        return base_price * 1.3


class SpecialTariffStrategy(PricingStrategy):
    """Стратегия: Специальный акционный тариф (-30% от цены)."""

    def calculate_price(self, base_price: float) -> float:
        return base_price * 0.7