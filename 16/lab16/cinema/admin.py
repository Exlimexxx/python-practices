"""Настройка административной панели Django для моделей кинотеатра."""

from __future__ import annotations

from django.contrib import admin
from django.db.models import Count
from django.utils.html import format_html

from .models import Genre, Hall, Movie, Session, Ticket

admin.site.site_header = "Кинотеатр — административная панель"
admin.site.site_title = "Кинотеатр"
admin.site.index_title = "Управление данными кинотеатра"


class SessionInline(admin.TabularInline):
    """Встроенный список сеансов на странице фильма."""

    model = Session
    extra = 0
    fields = ("hall", "start_time", "price", "status")
    ordering = ("start_time",)


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    """Администрирование жанров."""

    list_display = ("name", "slug", "movies_total")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("name",)

    @admin.display(description="Фильмов")
    def movies_total(self, obj: Genre) -> int:
        return obj.movies.count()

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(total=Count("movies"))


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    """Расширенная настройка Admin для основной модели Movie."""

    list_display = (
        "title",
        "year",
        "rating",
        "genres_list",
        "duration_minutes",
        "sessions_total",
        "is_active",
    )
    list_display_links = ("title",)
    list_filter = ("is_active", "genres", "year", "rating")
    search_fields = ("title", "description")
    list_editable = ("is_active",)
    list_per_page = 15
    date_hierarchy = "created_at"
    ordering = ("-rating", "title")
    filter_horizontal = ("genres",)
    inlines = [SessionInline]
    readonly_fields = ("created_at", "updated_at", "poster_preview")
    fieldsets = (
        ("Основные сведения", {"fields": ("title", "genres", "year", "rating")}),
        ("Описание", {"fields": ("description", "poster", "poster_preview")}),
        (
            "Прокат",
            {"fields": ("duration_minutes", "is_active", "created_at", "updated_at")},
        ),
    )
    actions = ("mark_active", "mark_inactive")

    @admin.display(description="Жанры")
    def genres_list(self, obj: Movie) -> str:
        return obj.genres_text

    @admin.display(description="Сеансов")
    def sessions_total(self, obj: Movie) -> int:
        return obj.sessions.count()

    @admin.display(description="Афиша")
    def poster_preview(self, obj: Movie):
        if not obj.poster:
            return "Афиша не загружена"
        return format_html(
            '<img src="{}" style="max-height: 180px;" alt="афиша" />', obj.poster.url
        )

    @admin.action(description="Вернуть в прокат")
    def mark_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"Возвращено в прокат: {updated}")

    @admin.action(description="Снять с проката")
    def mark_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Снято с проката: {updated}")

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .prefetch_related("genres")
            .annotate(sessions_count_ann=Count("sessions", distinct=True))
        )


@admin.register(Hall)
class HallAdmin(admin.ModelAdmin):
    """Администрирование залов."""

    list_display = ("name", "rows", "seats_per_row", "capacity", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "description")
    ordering = ("name",)


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    """Администрирование сеансов."""

    list_display = (
        "movie",
        "hall",
        "start_time",
        "end_time_display",
        "price",
        "status",
        "sold_count",
    )
    list_filter = ("status", "hall", "movie__genres", "start_time")
    search_fields = ("movie__title", "hall__name")
    autocomplete_fields = ()
    raw_id_fields = ()
    list_select_related = ("movie", "hall")
    date_hierarchy = "start_time"
    ordering = ("start_time",)

    @admin.display(description="Окончание")
    def end_time_display(self, obj: Session) -> str:
        return obj.end_time.strftime("%H:%M")

    @admin.display(description="Продано билетов")
    def sold_count(self, obj: Session) -> int:
        return obj.tickets.count()


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    """Администрирование билетов."""

    list_display = ("session", "row", "seat", "price", "buyer_name", "is_paid")
    list_filter = ("is_paid", "session__hall", "session__movie")
    search_fields = ("buyer_name", "session__movie__title")
    list_select_related = ("session", "session__movie")
    ordering = ("session", "row", "seat")
