"""Модели Django ORM предметной области «Кинотеатр» (вариант 4).

Сущности: Genre, Movie, Hall, Session, Ticket.
Связи: Movie — Genre (ManyToMany), Session — Movie (ForeignKey),
Session — Hall (ForeignKey), Ticket — Session (ForeignKey).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q, Sum
from django.urls import reverse
from django.utils import timezone

from .exceptions import HallInactiveError, SessionOverlapError

logger = logging.getLogger(__name__)


class Genre(models.Model):
    """Жанр фильма (боевик, драма, комедия и т. п.)."""

    name = models.CharField("Название жанра", max_length=60, unique=True)
    slug = models.SlugField("Слаг", max_length=60, unique=True, allow_unicode=True)
    description = models.TextField("Описание", blank=True, default="")

    class Meta:
        verbose_name = "Жанр"
        verbose_name_plural = "Жанры"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self) -> str:
        """Ссылка на список фильмов, отфильтрованный по этому жанру."""
        return f"{reverse('cinema:movie_list')}?genre={self.pk}"

    @property
    def movies_count(self) -> int:
        """Количество фильмов жанра (annotate/Count в статистике)."""
        return self.movies.count()


class Movie(models.Model):
    """Фильм кинотеатра — основная сущность предметной области."""

    title = models.CharField("Название", max_length=200, db_index=True)
    genres = models.ManyToManyField(
        Genre,
        verbose_name="Жанры",
        related_name="movies",
        blank=True,
        help_text="Один фильм может относиться к нескольким жанрам.",
    )
    year = models.PositiveSmallIntegerField(
        "Год выпуска",
        validators=[MinValueValidator(1895), MaxValueValidator(2100)],
        db_index=True,
    )
    rating = models.DecimalField(
        "Рейтинг (0-10)",
        max_digits=3,
        decimal_places=1,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        db_index=True,
    )
    description = models.TextField("Описание", blank=True, default="")
    poster = models.ImageField("Афиша", upload_to="posters/%Y/", blank=True, null=True)
    duration_minutes = models.PositiveSmallIntegerField(
        "Продолжительность сеанса, мин",
        validators=[MinValueValidator(1), MaxValueValidator(600)],
    )
    is_active = models.BooleanField("В прокате", default=True, db_index=True)
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлён", auto_now=True)

    class Meta:
        verbose_name = "Фильм"
        verbose_name_plural = "Фильмы"
        ordering = ["-rating", "title"]
        indexes = [
            models.Index(fields=["-rating", "title"], name="movie_rating_title_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(year__gte=1895) & Q(year__lte=2100),
                name="movie_year_range",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.year})"

    def get_absolute_url(self) -> str:
        return reverse("cinema:movie_detail", kwargs={"pk": self.pk})

    # --- валидация ---------------------------------------------------------

    def clean(self) -> None:
        """Проверка бизнес-правил фильма перед сохранением."""
        errors: dict[str, str] = {}
        if not self.title or not self.title.strip():
            errors["title"] = "Название фильма не может быть пустым."
        if self.year and self.year > timezone.now().year + 3:
            errors["year"] = "Год выпуска указан нереально далеко в будущем."
        if self.duration_minutes and self.duration_minutes > 240:
            logger.warning(
                "Фильм %s: необычно длинная продолжительность %s мин",
                self.title,
                self.duration_minutes,
            )
        if errors:
            raise ValidationError(errors)

    # --- вычисляемые свойства ---------------------------------------------

    @property
    def genres_text(self) -> str:
        """Строка жанров для list_display и шаблонов (без N+1 при prefetch)."""
        return ", ".join(genre.name for genre in self.genres.all()) or "—"

    @property
    def sessions_count(self) -> int:
        return self.sessions.count()

    @property
    def min_price(self):
        """Минимальная цена сеанса (агрегация ORM)."""
        return self.sessions.aggregate(value=models.Min("price"))["value"]

    def end_time_for(self, start: datetime) -> datetime:
        """Момент окончания сеанса, начавшегося в момент start."""
        return start + timedelta(minutes=self.duration_minutes)


class Hall(models.Model):
    """Кинозал с фиксированным числом рядов и мест."""

    name = models.CharField("Название зала", max_length=80, unique=True)
    rows = models.PositiveSmallIntegerField(
        "Количество рядов", validators=[MinValueValidator(1), MaxValueValidator(50)]
    )
    seats_per_row = models.PositiveSmallIntegerField(
        "Мест в ряду", validators=[MinValueValidator(1), MaxValueValidator(60)]
    )
    description = models.TextField("Описание", blank=True, default="")
    is_active = models.BooleanField("Действует", default=True, db_index=True)

    class Meta:
        verbose_name = "Зал"
        verbose_name_plural = "Залы"
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(
                condition=Q(rows__gte=1) & Q(seats_per_row__gte=1),
                name="hall_positive_size",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.capacity} мест)"

    def get_absolute_url(self) -> str:
        return reverse("cinema:hall_detail", kwargs={"pk": self.pk})

    @property
    def capacity(self) -> int:
        """Общее число мест в зале."""
        return self.rows * self.seats_per_row

    def clean(self) -> None:
        if self.capacity and self.capacity > 600:
            raise ValidationError(
                {"rows": "Суммарная вместимость зала превышает 600 мест."}
            )


class Session(models.Model):
    """Сеанс — показ фильма в конкретном зале в конкретное время."""

    class Status(models.TextChoices):
        PLANNED = "planned", "Запланирован"
        CANCELLED = "cancelled", "Отменён"
        FINISHED = "finished", "Завершён"

    movie = models.ForeignKey(
        Movie,
        verbose_name="Фильм",
        on_delete=models.PROTECT,
        related_name="sessions",
    )
    hall = models.ForeignKey(
        Hall,
        verbose_name="Зал",
        on_delete=models.PROTECT,
        related_name="sessions",
    )
    start_time = models.DateTimeField("Начало сеанса", db_index=True)
    price = models.DecimalField(
        "Цена билета",
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    status = models.CharField(
        "Статус",
        max_length=16,
        choices=Status.choices,
        default=Status.PLANNED,
        db_index=True,
    )
    created_at = models.DateTimeField("Создан", auto_now_add=True)

    class Meta:
        verbose_name = "Сеанс"
        verbose_name_plural = "Сеансы"
        ordering = ["start_time"]
        indexes = [
            models.Index(fields=["hall", "start_time"], name="session_hall_start_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.movie.title} - {self.start_time:%d.%m.%Y %H:%M} ({self.hall.name})"

    def get_absolute_url(self) -> str:
        return reverse("cinema:session_detail", kwargs={"pk": self.pk})

    # --- вычисляемые свойства ---------------------------------------------

    @property
    def end_time(self) -> datetime:
        """Время окончания сеанса = начало + продолжительность фильма."""
        return self.movie.end_time_for(self.start_time)

    @property
    def sold_tickets(self) -> int:
        return self.tickets.count()

    @property
    def free_seats(self) -> int:
        return self.hall.capacity - self.sold_tickets

    @property
    def revenue(self):
        """Выручка сеанса (агрегация Sum по проданным билетам)."""
        return self.tickets.aggregate(total=Sum("price"))["total"] or 0

    # --- валидация ---------------------------------------------------------

    def clean(self) -> None:
        errors: dict[str, str] = {}
        if self.hall_id and self.hall and not self.hall.is_active:
            errors["hall"] = "Нельзя назначить сеанс в неактивном зале."
        if self.movie_id and self.movie and not self.movie.is_active:
            errors["movie"] = "Фильм снят с проката."
        if self.start_time and self.movie_id and self.hall_id:
            conflict = (
                Session.objects.filter(hall_id=self.hall_id)
                .exclude(pk=self.pk)
                .exclude(status=self.Status.CANCELLED)
                .filter(start_time__lt=self.end_time)
                .filter(start_time__gte=self.start_time - timedelta(minutes=600))
            )
            for other in conflict:
                if other.start_time < self.end_time and other.end_time > self.start_time:
                    errors["start_time"] = (
                        f"Пересечение с сеансом «{other.movie.title}» "
                        f"({other.start_time:%H:%M}-{other.end_time:%H:%M})."
                    )
                    break
        if errors:
            raise ValidationError(errors)

    def assert_no_overlap(self) -> None:
        """Проверка пересечения сеансов через собственные исключения."""
        conflict = (
            Session.objects.filter(hall_id=self.hall_id)
            .exclude(pk=self.pk)
            .exclude(status=self.Status.CANCELLED)
            .filter(
                start_time__lt=self.end_time,
                start_time__gte=self.start_time - timedelta(hours=10),
            )
        )
        for other in conflict:
            if other.start_time < self.end_time and other.end_time > self.start_time:
                raise SessionOverlapError(
                    self.hall.name,
                    self.start_time.strftime("%d.%m.%Y %H:%M"),
                    self.end_time.strftime("%d.%m.%Y %H:%M"),
                )
        if self.hall and not self.hall.is_active:
            raise HallInactiveError(self.hall.name)


class Ticket(models.Model):
    """Проданный билет на конкретный сеанс (место в зале)."""

    session = models.ForeignKey(
        Session,
        verbose_name="Сеанс",
        on_delete=models.CASCADE,
        related_name="tickets",
    )
    row = models.PositiveSmallIntegerField("Ряд", validators=[MinValueValidator(1)])
    seat = models.PositiveSmallIntegerField("Место", validators=[MinValueValidator(1)])
    price = models.DecimalField(
        "Цена", max_digits=8, decimal_places=2, validators=[MinValueValidator(0)]
    )
    buyer_name = models.CharField("Покупатель", max_length=120)
    is_paid = models.BooleanField("Оплачен", default=True, db_index=True)
    purchased_at = models.DateTimeField("Продан", auto_now_add=True)

    class Meta:
        verbose_name = "Билет"
        verbose_name_plural = "Билеты"
        ordering = ["session", "row", "seat"]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "row", "seat"],
                name="unique_ticket_seat_per_session",
            ),
            models.CheckConstraint(
                condition=Q(row__gte=1) & Q(seat__gte=1),
                name="ticket_positive_position",
            ),
        ]

    def __str__(self) -> str:
        return f"Билет #{self.pk}: ряд {self.row}, место {self.seat} — {self.session}"

    def get_absolute_url(self) -> str:
        return reverse("cinema:session_detail", kwargs={"pk": self.session_id})

    def clean(self) -> None:
        """Проверка, что место существует в зале сеанса."""
        errors: dict[str, str] = {}
        if self.session_id and self.row and self.row > self.session.hall.rows:
            errors["row"] = f"В зале всего {self.session.hall.rows} рядов."
        if self.session_id and self.seat and self.seat > self.session.hall.seats_per_row:
            errors["seat"] = f"В ряду всего {self.session.hall.seats_per_row} мест."
        if errors:
            raise ValidationError(errors)
