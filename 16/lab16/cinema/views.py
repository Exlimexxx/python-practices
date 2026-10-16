"""Представления приложения «Кинотеатр»: FBV и CBV, CRUD, поиск, статистика."""

from __future__ import annotations

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.db.models.deletion import ProtectedError
from django.db.models import Count, F
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from .exceptions import CinemaError
from .forms import GenreForm, HallForm, MovieForm, MovieSearchForm, SessionForm, TicketForm
from .models import Genre, Hall, Movie, Session, Ticket
from .orm_demo import run_orm_demo, statistics_data
from .services import book_ticket

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------
# Миксины разграничения доступа
# --------------------------------------------------------------------------
class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Доступ только администратору (is_staff). Иначе — вход или 403."""

    def test_func(self) -> bool:
        return bool(self.request.user.is_staff)

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            logger.warning(
                "Отказано в доступе пользователю %s к %s",
                self.request.user.username,
                self.request.path,
            )
            raise PermissionDenied("Требуются права администратора.")
        return super().handle_no_permission()


# --------------------------------------------------------------------------
# FBV: главная, статистика, жанры, залы, ORM-демонстрация
# --------------------------------------------------------------------------
def index(request: HttpRequest) -> HttpResponse:
    """Главная страница: название, описание, счётчики, ссылки, текущий пользователь."""
    logger.info("Открыта главная страница пользователем %s", request.user)
    context = {
        "movies_total": Movie.objects.count(),
        "sessions_total": Session.objects.count(),
        "genres_total": Genre.objects.count(),
        "tickets_total": Ticket.objects.count(),
        "nearest_sessions": Session.objects.select_related("movie", "hall")
        .exclude(status=Session.Status.CANCELLED)
        .order_by("start_time")[:5],
        "top_movies": Movie.objects.prefetch_related("genres").order_by("-rating")[:5],
    }
    return render(request, "cinema/index.html", context)


def statistics(request: HttpRequest) -> HttpResponse:
    """Страница статистики: не менее четырёх показателей, рассчитанных ORM."""
    return render(request, "cinema/statistics.html", statistics_data())


def genre_list(request: HttpRequest) -> HttpResponse:
    """Список жанров с числом фильмов (annotate + Count)."""
    genres = Genre.objects.annotate(movies_total=Count("movies")).order_by("name")
    return render(request, "cinema/genre_list.html", {"genres": genres})


@login_required
def orm_demo(request: HttpRequest) -> HttpResponse:
    """Страница демонстрации ORM-запросов и проблемы N+1 (только для вошедших)."""
    return render(request, "cinema/orm_demo.html", {"lines": run_orm_demo()})


# --------------------------------------------------------------------------
# CBV: фильмы (ListView, DetailView, CreateView, UpdateView, DeleteView)
# --------------------------------------------------------------------------
class MovieListView(ListView):
    """Список фильмов с поиском, фильтрацией, сортировкой и пагинацией."""

    model = Movie
    template_name = "cinema/movie_list.html"
    context_object_name = "movies"
    paginate_by = 10  # 10 объектов на страницу (требование методички)

    def get_queryset(self):
        queryset = Movie.objects.prefetch_related("genres").annotate(
            sessions_total=Count("sessions", distinct=True)
        )
        self.search_form = MovieSearchForm(self.request.GET or None)
        if self.search_form.is_valid():
            data = self.search_form.cleaned_data
            if data.get("q"):
                queryset = queryset.filter(title__icontains=data["q"])
            if data.get("genre"):
                queryset = queryset.filter(genres=data["genre"])
            if data.get("year_from"):
                queryset = queryset.filter(year__gte=data["year_from"])
            if data.get("min_rating") is not None:
                queryset = queryset.filter(rating__gte=data["min_rating"])
            sort = data.get("sort") or "-rating"
        else:
            sort = "-rating"
        logger.info(
            "Список фильмов: GET=%s, сортировка=%s",
            self.request.GET.urlencode(),
            sort,
        )
        return queryset.order_by(sort)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = self.search_form
        context["total"] = context["paginator"].count if context.get("paginator") else 0
        return context


class MovieDetailView(DetailView):
    """Детальная страница фильма: сведения, жанры, сеансы, действия."""

    model = Movie
    template_name = "cinema/movie_detail.html"
    context_object_name = "movie"

    def get_queryset(self):
        return Movie.objects.prefetch_related("genres", "sessions__hall")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["sessions"] = (
            self.object.sessions.select_related("hall", "movie")
            .annotate(sold=Count("tickets"))
            .order_by("start_time")
        )
        context["similar"] = (
            Movie.objects.filter(genres__in=self.object.genres.all())
            .exclude(pk=self.object.pk)
            .prefetch_related("genres")
            .distinct()[:5]
        )
        return context


class MovieCreateView(StaffRequiredMixin, CreateView):
    """Создание фильма (доступно администратору)."""

    model = Movie
    form_class = MovieForm
    template_name = "cinema/movie_form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        logger.info("Создан фильм %r пользователем %s", self.object, self.request.user)
        messages.success(self.request, f"Фильм «{self.object.title}» добавлен.")
        return response


class MovieUpdateView(StaffRequiredMixin, UpdateView):
    """Редактирование фильма."""

    model = Movie
    form_class = MovieForm
    template_name = "cinema/movie_form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        logger.info("Изменён фильм %r пользователем %s", self.object, self.request.user)
        messages.success(self.request, f"Фильм «{self.object.title}» обновлён.")
        return response


class MovieDeleteView(StaffRequiredMixin, DeleteView):
    """Удаление фильма с подтверждением."""

    model = Movie
    template_name = "cinema/movie_confirm_delete.html"
    success_url = reverse_lazy("cinema:movie_list")

    def form_valid(self, form):
        movie = self.get_object()
        logger.warning("Удаление фильма %r пользователем %s", movie, self.request.user)
        try:
            response = super().form_valid(form)
        except ProtectedError:
            # Связь Session.movie объявлена с on_delete=PROTECT
            logger.error("Отказ в удалении фильма %r: есть связанные сеансы", movie)
            messages.error(
                self.request,
                f"Нельзя удалить фильм «{movie.title}»: с ним связаны сеансы.",
            )
            return HttpResponseRedirect(
                reverse("cinema:movie_detail", args=[movie.pk])
            )
        messages.warning(self.request, f"Фильм «{movie.title}» удалён.")
        return response


# --------------------------------------------------------------------------
# CBV: сеансы
# --------------------------------------------------------------------------
class SessionListView(ListView):
    """Расписание сеансов: фильтр по залу и статусу, сортировка, пагинация."""

    model = Session
    template_name = "cinema/session_list.html"
    context_object_name = "sessions"
    paginate_by = 10

    def get_queryset(self):
        queryset = Session.objects.select_related("movie", "hall").annotate(
            sold=Count("tickets")
        )
        hall_id = self.request.GET.get("hall")
        status = self.request.GET.get("status")
        sort = self.request.GET.get("sort", "start_time")
        if hall_id:
            queryset = queryset.filter(hall_id=hall_id)
        if status:
            queryset = queryset.filter(status=status)
        if sort not in {"start_time", "-start_time", "price", "-price"}:
            sort = "start_time"
        return queryset.order_by(sort)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["halls"] = Hall.objects.all()
        context["statuses"] = Session.Status.choices
        context["current_hall"] = self.request.GET.get("hall", "")
        context["current_status"] = self.request.GET.get("status", "")
        context["current_sort"] = self.request.GET.get("sort", "start_time")
        return context


class SessionDetailView(DetailView):
    """Сеанс: сведения о фильме и зале, проданные билеты, покупка билета."""

    model = Session
    template_name = "cinema/session_detail.html"
    context_object_name = "session"

    def get_queryset(self):
        return Session.objects.select_related("movie", "hall")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tickets"] = self.object.tickets.order_by("row", "seat")
        context["ticket_form"] = TicketForm()
        context["revenue"] = self.object.revenue
        return context


class SessionCreateView(StaffRequiredMixin, CreateView):
    """Создание сеанса (администратор)."""

    model = Session
    form_class = SessionForm
    template_name = "cinema/session_form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        logger.info("Создан сеанс %r пользователем %s", self.object, self.request.user)
        messages.success(self.request, "Сеанс добавлен в расписание.")
        return response


class SessionUpdateView(StaffRequiredMixin, UpdateView):
    """Редактирование сеанса."""

    model = Session
    form_class = SessionForm
    template_name = "cinema/session_form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        logger.info("Изменён сеанс %r пользователем %s", self.object, self.request.user)
        messages.success(self.request, "Сеанс обновлён.")
        return response


class SessionDeleteView(StaffRequiredMixin, DeleteView):
    """Удаление сеанса с подтверждением."""

    model = Session
    template_name = "cinema/session_confirm_delete.html"
    success_url = reverse_lazy("cinema:session_list")

    def form_valid(self, form):
        session = self.get_object()
        logger.warning("Удаление сеанса %r", session)
        try:
            response = super().form_valid(form)
        except ProtectedError:
            logger.error("Отказ в удалении сеанса %r", session)
            messages.error(self.request, "Сеанс связан с защищёнными объектами.")
            return HttpResponseRedirect(
                reverse("cinema:session_detail", args=[session.pk])
            )
        messages.warning(self.request, "Сеанс удалён.")
        return response


class HallDetailView(DetailView):
    """Детальная страница зала со списком сеансов."""

    model = Hall
    template_name = "cinema/hall_detail.html"
    context_object_name = "hall"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["sessions"] = self.object.sessions.select_related("movie").order_by(
            "start_time"
        )
        return context


# --------------------------------------------------------------------------
# Покупка билета: FBV + собственные исключения
# --------------------------------------------------------------------------
@login_required
@require_POST
def buy_ticket(request: HttpRequest, pk: int) -> HttpResponse:
    """Продать билет на сеанс. Демонстрирует собственные исключения."""
    session = get_object_or_404(Session.objects.select_related("movie", "hall"), pk=pk)
    form = TicketForm(request.POST)
    if form.is_valid():
        try:
            ticket = book_ticket(
                session,
                form.cleaned_data["row"],
                form.cleaned_data["seat"],
                form.cleaned_data["buyer_name"],
                price=session.price,
            )
        except CinemaError as exc:
            logger.warning("Ошибка продажи билета: %s", exc)
            messages.error(request, str(exc))
        else:
            messages.success(
                request,
                f"Билет #{ticket.pk} продан: ряд {ticket.row}, место {ticket.seat}.",
            )
    else:
        messages.error(request, "Некорректные данные формы билета.")
    return HttpResponseRedirect(reverse("cinema:session_detail", args=[session.pk]))


# --------------------------------------------------------------------------
# Обработчики ошибок
# --------------------------------------------------------------------------
def custom_404(request: HttpRequest, exception: Exception) -> HttpResponse:
    """Собственная страница 404 с логированием."""
    logger.warning("404: страница не найдена — %s", request.path)
    return render(request, "cinema/404.html", status=404)


def custom_500(request: HttpRequest) -> HttpResponse:
    """Собственная страница 500 с логированием."""
    logger.error("500: внутренняя ошибка сервера — %s", request.path)
    return render(request, "cinema/500.html", status=500)
