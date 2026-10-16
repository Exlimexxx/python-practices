from typing import Protocol


class Notifier(Protocol):
    """ISP: Интерфейс для отправки уведомлений."""

    def notify(self, message: str) -> None:
        ...