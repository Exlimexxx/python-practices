from dataclasses import dataclass, field
from enum import Enum


class SessionStatus(Enum):
    """Статусы сеанса в кинотеатре."""
    SCHEDULED = "Запланирован"
    IN_PROGRESS = "Идёт"
    COMPLETED = "Завершён"
    CANCELLED = "Отменён"


# Пользовательские исключения
class CinemaError(Exception):
    """Базовое исключение для предметной области Кинотеатр."""
    pass


class EntityNotFoundError(CinemaError):
    """Вызывается, если запрашиваемый объект не найден."""
    pass


class InvalidStatusError(CinemaError):
    """Вызывается при попытке выполнить недопустимую смену статуса."""
    pass


class CapacityExceededError(CinemaError):
    """Вызывается, если количество билетов превышает вместимость зала."""
    pass


@dataclass
class Entity:
    """Базовый класс сущностей предметной области."""
    id: int
    name: str


@dataclass
class Hall(Entity):
    """Модель кинозала."""
    capacity: int
    is_vip: bool = False

    def get_report_data(self) -> str:
        """Реализация интерфейса Reportable."""
        vip_str = "VIP" if self.is_vip else "Стандарт"
        return f"Зал №{self.id} '{self.name}' ({vip_str}) — Вместимость: {self.capacity} мест"


@dataclass
class Movie(Entity):
    """Модель фильма."""
    duration_minutes: int
    genre: str
    ticket_price: float

    def get_report_data(self) -> str:
        """Реализация интерфейса Reportable."""
        return (f"Фильм '{self.name}' [ID: {self.id}] — Жанр: {self.genre}, "
                f"Длительность: {self.duration_minutes} мин., Цена: {self.ticket_price:.2f} руб.")


@dataclass
class Session(Entity):
    """Модель киносеанса."""
    movie: Movie
    hall: Hall
    sold_tickets: int = 0
    status: SessionStatus = SessionStatus.SCHEDULED

    def get_report_data(self) -> str:
        """Реализация интерфейса Reportable."""
        occupancy = (self.sold_tickets / self.hall.capacity * 100) if self.hall.capacity > 0 else 0
        return (f"Сеанс #{self.id} ({self.name}) — Фильм: '{self.movie.name}', Зал: '{self.hall.name}', "
                f"Статус: {self.status.value}, Продано билетов: {self.sold_tickets}/{self.hall.capacity} ({occupancy:.1f}%)")

    def change_status(self, new_status: SessionStatus) -> None:
        """Метод изменения состояния сеанса с валидацией."""
        if self.status == SessionStatus.CANCELLED:
            raise InvalidStatusError(f"Нельзя изменить статус отменённого сеанса #{self.id}.")
        self.status = new_status