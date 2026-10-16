"""Демонстрация обязательных запросов Django ORM и проблемы N+1."""

from __future__ import annotations

import logging

from django.db import connection
from django.db.models import Avg, Count, Max, Min, Sum
from django.test.utils import CaptureQueriesContext

from .models import Genre, Hall, Movie, Session, Ticket

logger = logging.getLogger(__name__)


def run_orm_demo() -> list[str]:
    """Выполнить обязательный набор ORM-запросов и вернуть строки отчёта."""
    lines: list[str] = []

    def add(title: str, value: object) -> None:
        lines.append(f"{title}: {value}")

    # all()
    add("all() — всего фильмов", Movie.objects.all().count())
    # filter()
    add(
        "filter(rating__gte=8) — фильмов с высоким рейтингом",
        Movie.objects.filter(rating__gte=8).count(),
    )
    # exclude()
    add(
        "exclude(is_active=True) — снятых с проката",
        Movie.objects.exclude(is_active=True).count(),
    )
    # get()
    first = Movie.objects.order_by("pk").first()
    add("get(pk=...) — найден фильм", f"{first!r}" if first else "нет данных")
    # order_by()
    top3 = list(Movie.objects.order_by("-rating", "title")[:3])
    add("order_by('-rating') — топ-3", [m.title for m in top3])
    # count()
    add("count() — количество сеансов", Session.objects.count())
    # exists()
    add(
        "exists() — есть ли сеанс дороже 500",
        Session.objects.filter(price__gt=500).exists(),
    )
    # aggregate()
    agg = Session.objects.aggregate(
        min_price=Min("price"),
        max_price=Max("price"),
        avg_price=Avg("price"),
        tickets=Sum("price"),
    )
    add("aggregate() по сеансам", agg)
    # annotate()
    by_genre = (
        Genre.objects.annotate(movies_total=Count("movies"))
        .order_by("-movies_total")[:5]
        .values_list("name", "movies_total")
    )
    add("annotate() — фильмов по жанрам (топ-5)", list(by_genre))
    # связи
    session = Session.objects.select_related("movie", "hall").first()
    if session:
        add(
            "связанные объекты",
            f"сеанс #{session.pk}: {session.movie.title} в зале {session.hall.name}, "
            f"билетов {session.tickets.count()}",
        )
        add(
            "обратный доступ: hall.sessions",
            session.hall.sessions.count(),
        )
    m2m = Movie.objects.prefetch_related("genres").first()
    if m2m:
        add("M2M genres", f"{m2m.title} -> {[g.name for g in m2m.genres.all()]}")

    # N+1
    with CaptureQueriesContext(connection) as naive:
        titles = [f"{s.movie.title} / {s.hall.name}" for s in Session.objects.all()]
    with CaptureQueriesContext(connection) as optimized:
        opt_titles = [
            f"{s.movie.title} / {s.hall.name}"
            for s in Session.objects.select_related("movie", "hall")
        ]
    lines.append("")
    lines.append("=== Проблема N+1 ===")
    lines.append(
        f"Плохой вариант (Session.objects.all() без select_related): "
        f"{len(naive)} SQL-запроса на {len(titles)} сеансов"
    )
    lines.append(
        f"Улучшенный вариант (select_related('movie','hall')): "
        f"{len(optimized)} SQL-запроса на {len(opt_titles)} сеансов"
    )
    lines.append(
        "Преимущество prefetch_related показано на жанрах (M2M) и билетах (обратный FK)."
    )
    with CaptureQueriesContext(connection) as prefetch_stats:
        for movie in Movie.objects.prefetch_related("genres"):
            _ = movie.genres_text
    with CaptureQueriesContext(connection) as naive_stats:
        for movie in Movie.objects.all():
            _ = movie.genres_text
    lines.append(
        f"Жанры: prefetch_related — {len(prefetch_stats)} запросов, "
        f"наивный обход — {len(naive_stats)} запросов"
    )
    logger.info("ORM-демонстрация выполнена, строк отчёта: %s", len(lines))
    return lines


def statistics_data() -> dict[str, object]:
    """Показатели для страницы статистики (вычисляются средствами ORM)."""
    return {
        "movies_total": Movie.objects.count(),
        "active_movies": Movie.objects.filter(is_active=True).count(),
        "genres_total": Genre.objects.count(),
        "halls_total": Hall.objects.count(),
        "sessions_total": Session.objects.count(),
        "tickets_total": Ticket.objects.count(),
        "tickets_revenue": Ticket.objects.aggregate(v=Sum("price"))["v"] or 0,
        "avg_rating": Movie.objects.aggregate(v=Avg("rating"))["v"] or 0,
        "avg_ticket_price": Session.objects.aggregate(v=Avg("price"))["v"] or 0,
        "top_genre": Genre.objects.annotate(total=Count("movies"))
        .order_by("-total")
        .first(),
        "top_movies": Movie.objects.annotate(total=Count("sessions__tickets"))
        .order_by("-total", "-rating")[:5],
        "hall_load": Hall.objects.annotate(total=Count("sessions")).order_by("-total"),
    }
