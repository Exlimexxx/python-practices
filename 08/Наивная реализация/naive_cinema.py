# naive_cinema.py


class NaiveCinemaSystem:

    def __init__(self):
        self.sessions = {}
        self.tickets = {}
        self.ticket_counter = 1

    def create_session(self, session_id: int, movie_title: str, base_price: float):
        self.sessions[session_id] = {
            "movie": movie_title,
            "base_price": base_price,
        }

    # НАИВНАЯ ЛОГИКА: Огромное количество ветвлений if-elif
    def process_action(self, action: str, **kwargs):
        if action == "buy_ticket":
            session_id = kwargs.get("session_id")
            ticket_type = kwargs.get("ticket_type")  # standard, vip, student
            day_type = kwargs.get("day_type")  # weekday, weekend, special

            session = self.sessions.get(session_id)
            if not session:
                raise ValueError("Сеанс не найден")

            # 1. Расчёт цены по дням (Наивная Стратегия)
            price = session["base_price"]
            if day_type == "weekday":
                price *= 1.0
            elif day_type == "weekend":
                price *= 1.3
            elif day_type == "special":
                price *= 0.7
            else:
                raise ValueError("Неизвестный тип дня")

            # 2. Модификация билета по типам (Наивная Фабрика)
            if ticket_type == "standard":
                pass
            elif ticket_type == "vip":
                price += 200.0  # Наценка за комфорт
            elif ticket_type == "student":
                price *= 0.5  # Скидка 50%
            else:
                raise ValueError("Неизвестный тип билета")

            ticket_id = self.ticket_counter
            ticket_data = {
                "ticket_id": ticket_id,
                "session_id": session_id,
                "type": ticket_type,
                "final_price": price,
                "active": True,
            }
            self.tickets[ticket_id] = ticket_data
            self.ticket_counter += 1
            return ticket_data

        elif action == "refund_ticket":
            ticket_id = kwargs.get("ticket_id")
            ticket = self.tickets.get(ticket_id)
            if ticket and ticket["active"]:
                ticket["active"] = False
                return True
            return False

        else:
            raise ValueError("Неизвестная команда")