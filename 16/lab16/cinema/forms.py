"""Формы Django: ModelForm для CRUD и Form для поиска/фильтрации."""

from __future__ import annotations

from django import forms
from django.core.exceptions import ValidationError

from .models import Genre, Hall, Movie, Session, Ticket

#: Варианты сортировки списка фильмов: ключ -> подпись
MOVIE_SORT_CHOICES = [
    ("-rating", "Рейтинг (по убыванию)"),
    ("rating", "Рейтинг (по возрастанию)"),
    ("title", "Название (А-Я)"),
    ("-title", "Название (Я-А)"),
    ("-year", "Год (сначала новые)"),
    ("year", "Год (сначала старые)"),
    ("duration_minutes", "Продолжительность (по возрастанию)"),
    ("-duration_minutes", "Продолжительность (по убыванию)"),
]


class MovieForm(forms.ModelForm):
    """Форма создания и редактирования фильма (ModelForm + валидация)."""

    class Meta:
        model = Movie
        fields = [
            "title",
            "genres",
            "year",
            "rating",
            "description",
            "poster",
            "duration_minutes",
            "is_active",
        ]
        widgets = {
            "title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Например: Матрица"}
            ),
            "genres": forms.SelectMultiple(attrs={"class": "form-select", "size": 6}),
            "year": forms.NumberInput(attrs={"class": "form-control", "min": 1895}),
            "rating": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.1", "min": 0, "max": 10}
            ),
            "description": forms.Textarea(
                attrs={"class": "form-control", "rows": 4}
            ),
            "duration_minutes": forms.NumberInput(
                attrs={"class": "form-control", "min": 1, "max": 600}
            ),
        }
        labels = {"is_active": "Показывается в прокате"}
        help_texts = {"rating": "Значение от 0.0 до 10.0"}

    def clean_title(self) -> str:
        """Название не должно быть пустым и не должно дублироваться."""
        title = (self.cleaned_data["title"] or "").strip()
        if len(title) < 2:
            raise ValidationError("Название должно содержать минимум 2 символа.")
        qs = Movie.objects.filter(title__iexact=title)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("Фильм с таким названием уже добавлен.")
        return title

    def clean_rating(self):
        rating = self.cleaned_data["rating"]
        if rating is None or not (0 <= rating <= 10):
            raise ValidationError("Рейтинг должен быть в диапазоне от 0 до 10.")
        return rating

    def clean_duration_minutes(self) -> int:
        duration = self.cleaned_data["duration_minutes"]
        if duration < 5:
            raise ValidationError("Продолжительность не может быть меньше 5 минут.")
        return duration

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("genres") and not cleaned.get("is_active"):
            raise ValidationError(
                "Неактивный фильм без жанров нельзя сохранить: заполните жанры."
            )
        return cleaned


class SessionForm(forms.ModelForm):
    """Форма создания и редактирования сеанса с проверкой пересечений."""

    class Meta:
        model = Session
        fields = ["movie", "hall", "start_time", "price", "status"]
        widgets = {
            "movie": forms.Select(attrs={"class": "form-select"}),
            "hall": forms.Select(attrs={"class": "form-select"}),
            "start_time": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "price": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": 0}
            ),
            "status": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fields["start_time"].input_formats = ["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M"]
        self.fields["movie"].queryset = Movie.objects.filter(is_active=True)
        self.fields["hall"].queryset = Hall.objects.filter(is_active=True)

    def clean_price(self):
        price = self.cleaned_data["price"]
        if price is not None and price > 100000:
            raise ValidationError("Слишком большая цена билета.")
        return price

    def clean(self):
        """Дополнительная проверка: пересечение сеансов в одном зале."""
        cleaned = super().clean()
        start = cleaned.get("start_time")
        hall = cleaned.get("hall")
        movie = cleaned.get("movie")
        if start and hall and movie:
            end = movie.end_time_for(start)
            qs = (
                Session.objects.filter(hall=hall)
                .exclude(status=Session.Status.CANCELLED)
                .select_related("movie")
            )
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            for other in qs:
                if other.start_time < end and other.end_time > start:
                    raise ValidationError(
                        f"В зале «{hall.name}» уже идёт сеанс "
                        f"«{other.movie.title}» ({other.start_time:%H:%M}-"
                        f"{other.end_time:%H:%M})."
                    )
        return cleaned


class TicketForm(forms.ModelForm):
    """Форма покупки билета (место в зале)."""

    class Meta:
        model = Ticket
        fields = ["row", "seat", "buyer_name", "is_paid"]
        widgets = {
            "row": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "seat": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "buyer_name": forms.TextInput(attrs={"class": "form-control"}),
        }

    def clean_buyer_name(self) -> str:
        name = (self.cleaned_data["buyer_name"] or "").strip()
        if len(name) < 3:
            raise ValidationError("Укажите ФИО покупателя (минимум 3 символа).")
        return name


class GenreForm(forms.ModelForm):
    """Форма жанра."""

    class Meta:
        model = Genre
        fields = ["name", "slug", "description"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "slug": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class HallForm(forms.ModelForm):
    """Форма зала."""

    class Meta:
        model = Hall
        fields = ["name", "rows", "seats_per_row", "description", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "rows": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "seats_per_row": forms.NumberInput(
                attrs={"class": "form-control", "min": 1}
            ),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class MovieSearchForm(forms.Form):
    """Форма поиска, фильтрации и сортировки списка фильмов."""

    q = forms.CharField(
        label="Поиск по названию",
        required=False,
        max_length=100,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Например: матрица"}
        ),
    )
    genre = forms.ModelChoiceField(
        label="Жанр",
        queryset=Genre.objects.all(),
        required=False,
        empty_label="Все жанры",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    year_from = forms.IntegerField(
        label="Год от",
        required=False,
        min_value=1895,
        max_value=2100,
        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "1990"}),
    )
    min_rating = forms.DecimalField(
        label="Рейтинг не ниже",
        required=False,
        min_value=0,
        max_value=10,
        widget=forms.NumberInput(
            attrs={"class": "form-control", "step": "0.1", "placeholder": "7.0"}
        ),
    )
    sort = forms.ChoiceField(
        label="Сортировка",
        choices=MOVIE_SORT_CHOICES,
        required=False,
        initial="-rating",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def clean_q(self) -> str:
        return (self.cleaned_data.get("q") or "").strip()
