from enum import Enum


class OrderStatus(Enum):
    NEW = "new"
    PAID = "paid"
    CANCELLED = "cancelled"


# --- Проблемная иерархия товаров ---
class Product:

    def __init__(self, product_id: int, name: str, price: float, weight: float):
        self.product_id = product_id
        self.name = name
        self.price = price
        self.weight = weight

    def calculate_shipping_cost(self) -> float:
        return self.weight * 1.5


class DigitalProduct(Product):

    def __init__(self, product_id: int, name: str, price: float):
        # Электронный товар не имеет веса, но вынужден передавать 0.0
        super().__init__(product_id, name, price, weight=0.0)

    def calculate_shipping_cost(self) -> float:
        # Нарушение LSP: электронный товар бросает исключение там,
        # где клиентский код ожидает числовое значение стоимости доставки.
        raise NotImplementedError(
            "Цифровые товары не требуют физической доставки!"
        )


# --- Чрезмерно раздутый интерфейс (Fat Interface) ---
class IOrderProcessor:

    def create_order(self, order_id: int):
        pass

    def process_payment(self, payment_type: str, amount: float):
        pass

    def send_email_notification(self, email: str, message: str):
        pass

    def send_sms_notification(self, phone: str, message: str):
        pass

    def export_to_pdf(self, order_id: int):
        pass

    def print_receipt(self, order_id: int):
        pass


# --- Класс "Бог" (God Object) с кучей ответственности ---
class OrderManager(IOrderProcessor):

    def __init__(self):
        # Жёсткая завязка на конкретную БД (в памяти)
        self.orders_db = {}

    def create_order(self, order_id: int):
        self.orders_db[order_id] = {"status": OrderStatus.NEW.value, "items": []}
        print(f"[UI/Log] Заказ #{order_id} создан.")  # Прямая работа с консолью

    # Нарушение OCP: условная конструкция для способов оплаты
    def process_payment(self, payment_type: str, amount: float):
        if payment_type == "card":
            print(f"Списание {amount} руб. с банковской карты...")
        elif payment_type == "cash":
            print(f"Получено {amount} руб. наличными...")
        elif payment_type == "crypto":
            print(f"Перевод {amount} USDT на криптокошелек...")
        else:
            raise ValueError(f"Неподдерживаемый способ оплаты: {payment_type}")

    # Принудительная реализация ненужных методов из раздутого интерфейса
    def send_email_notification(self, email: str, message: str):
        print(f"Отправка Email на {email}: {message}")

    def send_sms_notification(self, phone: str, message: str):
        # Нарушение ISP: если сервис отправляет только Email, метод все равно нужно реализовывать
        raise NotImplementedError("SMS уведомления не поддерживаются!")

    def export_to_pdf(self, order_id: int):
        print(f"Экспорт заказа #{order_id} в PDF...")

    def print_receipt(self, order_id: int):
        print(f"Печать чека для заказа #{order_id}...")