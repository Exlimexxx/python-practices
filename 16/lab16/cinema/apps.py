"""Конфигурация приложения cinema."""

from django.apps import AppConfig


class CinemaConfig(AppConfig):
    """Приложение «Кинотеатр»: фильмы, залы, сеансы и билеты."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "cinema"
    verbose_name = "Кинотеатр"
