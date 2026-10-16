from interfaces.payment import PaymentMethod


class CardPayment(PaymentMethod):

    def __init__(self, card_number: str) -> None:
        self.card_number = card_number

    def process_payment(self, amount: float) -> bool:
        print(
            f"[Шлюз Банка] Оплата {amount:.2f} руб. по карте **** {self.card_number[-4:]} прошла успешно."
        )
        return True


class CashPayment(PaymentMethod):

    def process_payment(self, amount: float) -> bool:
        print(
            f"[Касса Кинотеатра] Принято {amount:.2f} руб. наличными в кассу."
        )
        return True


class PushkinCardPayment(PaymentMethod):

    def __init__(self, card_id: str) -> None:
        self.card_id = card_id

    def process_payment(self, amount: float) -> bool:
        print(
            f"[Госуслуги] Средства ({amount:.2f} руб.) списаны с Пушкинской карты #{self.card_id}."
        )
        return True