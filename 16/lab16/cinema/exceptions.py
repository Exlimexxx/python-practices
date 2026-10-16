"""Собственная иерархия исключений предметной области «Кинотеатр»."""

from __future__ import annotations


class CinemaError(Exception):
    """Базовое исключение для всех ошибок предметной области кинотеатра."""


class ValidationCinemaError(CinemaError):
    """Базовое исключение ошибок валидации бизнес-правил."""


class SeatAlreadyTakenError(ValidationCinemaError):
    """Запрошенное место в зале уже продано на этот сеанс."""

    def __init__(self, row: int, seat: int, session_id: int) -> None:
        self.row = row
        self.seat = seat
        self.session_id = session_id
        super().__init__(
            f"Место (ряд {row}, место {seat}) уже занято на сеансе #{session_id}."
        )


class SeatOutOfHallError(ValidationCinemaError):
    """Номер ряда или места выходит за границы зала."""

    def __init__(self, row: int, seat: int, rows: int, seats_per_row: int) -> None:
        self.row = row
        self.seat = seat
        super().__init__(
            f"Место (ряд {row}, место {seat}) отсутствует в зале: "
            f"доступны ряды 1..{rows}, места 1..{seats_per_row}."
        )


class SessionOverlapError(ValidationCinemaError):
    """Сеанс пересекается по времени с другим сеансом в том же зале."""

    def __init__(self, hall_name: str, start: str, end: str) -> None:
        self.hall_name = hall_name
        super().__init__(
            f"Зал «{hall_name}» занят в интервале {start} — {end}."
        )


class HallInactiveError(ValidationCinemaError):
    """Попытка использовать закрытый зал."""

    def __init__(self, hall_name: str) -> None:
        self.hall_name = hall_name
        super().__init__(f"Зал «{hall_name}» не активен и недоступен для сеансов.")
