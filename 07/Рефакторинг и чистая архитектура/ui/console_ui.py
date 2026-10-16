from services.cinema_service import CinemaService


class ConsoleUI:
    """SRP: Отвечает только за красивый вывод информации в консоль."""

    def __init__(self, cinema_service: CinemaService) -> None:
        self.cinema_service = cinema_service

    def show_report(self) -> None:
        report_text = self.cinema_service.get_financial_report()
        print("\n" + report_text + "\n")