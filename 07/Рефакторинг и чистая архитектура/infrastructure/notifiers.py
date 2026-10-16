from interfaces.notifier import Notifier


class ConsoleNotifier(Notifier):

    def notify(self, message: str) -> None:
        print(f"[Системный лог]: {message}")


class EmailNotifier(Notifier):

    def __init__(self, email: str) -> None:
        self.email = email

    def notify(self, message: str) -> None:
        print(f"[Email на {self.email}]: {message}")