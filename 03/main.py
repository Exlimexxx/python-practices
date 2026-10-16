class Product:
    def __init__(self, name: str, price: float):
        self.name = name
        self.price = max(0.0, float(price))

    def delivery(self) -> float:
        return 0.0

    def info(self) -> str:
        return f"{self.name} | Цена: {self.price} руб."


class PhysicalProduct(Product):
    def __init__(self, name: str, price: float, weight: float):
        super().__init__(name, price)
        self.weight = float(weight)

    def delivery(self) -> float:
        return 200.0 + self.weight * 50.0  # 200 базово + 50 за кг

    def info(self) -> str:
        return f"[Физический] {super().info()} | Вес: {self.weight} кг | Доставка: {self.delivery()} руб."


class DigitalProduct(Product):
    def __init__(self, name: str, price: float, size_mb: float):
        super().__init__(name, price)
        self.size_mb = float(size_mb)

    def info(self) -> str:
        return f"[Цифровой] {super().info()} | Размер: {self.size_mb} МБ | Доставка: Бесплатно"


class Order:
    def __init__(self, order_id: int):
        self.order_id = order_id
        self.products = []

    def show(self):
        print(f"\n--- Детали Заказа №{self.order_id} ---")
        if not self.products:
            return print("Заказ пуст.")

        total = 0.0
        for p in self.products:
            print(p.info())
            total += p.price + p.delivery()
        print(f"Итого к оплате: {total} руб.")


def main():
    order = Order(1)
    while True:
        choice = input("\n1. Физ. товар | 2. Цифровой | 3. Заказ | 0. Выход: ")
        if choice == "1":
            order.products.append(PhysicalProduct(input("Название: "), input("Цена: "), input("Вес (кг): ")))
            print("Товар добавлен!")
        elif choice == "2":
            order.products.append(DigitalProduct(input("Название: "), input("Цена: "), input("Размер (МБ): ")))
            print("Товар добавлен!")
        elif choice == "3":
            order.show()
        elif choice == "0":
            break


if __name__ == "__main__":
    main()