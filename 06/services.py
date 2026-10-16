import inspect
from typing import Any, List, Dict
from models import Entity, Movie, Hall, Session, SessionStatus, EntityNotFoundError, CapacityExceededError
from decorators import log_call, measure_time


def inspect_object(obj: Any) -> str:
    """
    Функция интроспекции объекта.
    Использует: type(), isinstance(), dir(), hasattr(), getattr(), inspect.signature().
    """
    lines: List[str] = []
    lines.append("=" * 50)
    lines.append(f"=== ИНФОРМАЦИЯ ОБ ОБЪЕКТЕ ===")
    lines.append(f"Тип: {type(obj)}")
    lines.append(f"Класс: {obj.__class__.__name__}")

    # Проверка принадлежности к базовому классу
    if isinstance(obj, Entity):
        lines.append(f"Сущность ID: {obj.id}, Наименование: {obj.name}")

    lines.append("\n[Атрибуты и значения]:")
    # Используем dir(), hasattr(), getattr()
    for attr in dir(obj):
        if not attr.startswith("_"):
            val = getattr(obj, attr)
            if not callable(val):
                lines.append(f"  • {attr}: {val}")

    lines.append("\n[Методы и сигнатуры]:")
    for attr in dir(obj):
        if not attr.startswith("_"):
            val = getattr(obj, attr)
            if callable(val):
                try:
                    sig = inspect.signature(val)
                    lines.append(f"  • {attr}{sig}")
                except (ValueError, TypeError):
                    lines.append(f"  • {attr}(...)")

    lines.append("=" * 50)
    return "\n".join(lines)


class CinemaService:
    """Сервис управления объектами кинотеатра."""

    def __init__(self) -> None:
        self.movies: Dict[int, Movie] = {}
        self.halls: Dict[int, Hall] = {}
        self.sessions: Dict[int, Session] = {}

    # --- Управление Фильмами ---
    def add_movie(self, movie: Movie) -> None:
        self.movies[movie.id] = movie

    # --- Управление Залами ---
    def add_hall(self, hall: Hall) -> None:
        self.halls[hall.id] = hall

    # --- Управление Сеансами ---
    @log_call
    def add_session(self, session: Session) -> None:
        self.sessions[session.id] = session

    def get_session(self, session_id: int) -> Session:
        if session_id not in self.sessions:
            raise EntityNotFoundError(f"Сеанс с ID {session_id} не найден.")
        return self.sessions[session_id]

    def remove_session(self, session_id: int) -> Session:
        session = self.get_session(session_id)
        del self.sessions[session_id]
        return session

    # --- Специализированные операции ---
    @measure_time
    def calculate_hall_occupancy(self, session_id: int) -> float:
        """Расчёт процента загрузки зала для конкретного сеанса."""
        session = self.get_session(session_id)
        if session.hall.capacity == 0:
            return 0.0
        return (session.sold_tickets / session.hall.capacity) * 100.0

    @measure_time
    def sell_tickets(self, session_id: int, count: int) -> None:
        """Покупка билетов на сеанс."""
        session = self.get_session(session_id)
        if session.sold_tickets + count > session.hall.capacity:
            raise CapacityExceededError(
                f"Нельзя продать {count} билетов. Доступно мест: {session.hall.capacity - session.sold_tickets}"
            )
        session.sold_tickets += count

    def get_popular_movies(self, top_n: int = 3) -> List[tuple[str, int]]:
        """Поиск наиболее популярных фильмов по количеству проданных билетов (с использованием map/filter/sorted)."""
        movie_sales: Dict[str, int] = {}

        # Агрегация проданных билетов по фильмам
        for session in self.sessions.values():
            m_name = session.movie.name
            movie_sales[m_name] = movie_sales.get(m_name, 0) + session.sold_tickets

        # Сортировка с использованием sorted
        sorted_movies = sorted(movie_sales.items(), key=lambda item: item[1], reverse=True)
        return sorted_movies[:top_n]

    # --- Формирование статистики ---
    @measure_time
    def get_statistics(self) -> Dict[str, Any]:
        """Расчёт общей статистики с использованием функциональных средств Python."""
        session_list = list(self.sessions.values())
        total_sessions = len(session_list)

        if total_sessions == 0:
            return {"total_sessions": 0}

        # Фильтрация активных и завершённых сеансов через filter
        active_sessions = list(
            filter(lambda s: s.status in (SessionStatus.SCHEDULED, SessionStatus.IN_PROGRESS), session_list))
        completed_sessions = list(filter(lambda s: s.status == SessionStatus.COMPLETED, session_list))

        # Получение массива проданных билетов через map
        tickets_sold = list(map(lambda s: s.sold_tickets, session_list))
        total_tickets = sum(tickets_sold)

        # Вычисление выручки с использованием comprehensions
        total_revenue = sum(s.sold_tickets * s.movie.ticket_price for s in session_list)

        avg_tickets = total_tickets / total_sessions if total_sessions > 0 else 0.0
        min_tickets = min(tickets_sold) if tickets_sold else 0
        max_tickets = max(tickets_sold) if tickets_sold else 0

        # Проверка условий через any и all
        has_full_house = any(s.sold_tickets == s.hall.capacity for s in session_list)
        all_scheduled = all(s.status == SessionStatus.SCHEDULED for s in session_list)

        return {
            "total_sessions": total_sessions,
            "active_sessions_count": len(active_sessions),
            "completed_sessions_count": len(completed_sessions),
            "total_tickets_sold": total_tickets,
            "total_revenue_rub": total_revenue,
            "avg_tickets_per_session": avg_tickets,
            "min_tickets_in_session": min_tickets,
            "max_tickets_in_session": max_tickets,
            "has_full_house": has_full_house,
            "all_scheduled": all_scheduled
        }