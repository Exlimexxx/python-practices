"""Маршрутизация приложения cinema."""

from django.urls import path

from . import views

app_name = "cinema"

urlpatterns = [
    # главные страницы
    path("", views.index, name="index"),
    path("statistics/", views.statistics, name="statistics"),
    path("genres/", views.genre_list, name="genre_list"),
    path("orm-demo/", views.orm_demo, name="orm_demo"),
    # фильмы (CRUD через CBV)
    path("movies/", views.MovieListView.as_view(), name="movie_list"),
    path("movies/create/", views.MovieCreateView.as_view(), name="movie_create"),
    path("movies/<int:pk>/", views.MovieDetailView.as_view(), name="movie_detail"),
    path("movies/<int:pk>/edit/", views.MovieUpdateView.as_view(), name="movie_update"),
    path(
        "movies/<int:pk>/delete/",
        views.MovieDeleteView.as_view(),
        name="movie_delete",
    ),
    # расписание сеансов
    path("sessions/", views.SessionListView.as_view(), name="session_list"),
    path("sessions/create/", views.SessionCreateView.as_view(), name="session_create"),
    path("sessions/<int:pk>/", views.SessionDetailView.as_view(), name="session_detail"),
    path(
        "sessions/<int:pk>/edit/",
        views.SessionUpdateView.as_view(),
        name="session_update",
    ),
    path(
        "sessions/<int:pk>/delete/",
        views.SessionDeleteView.as_view(),
        name="session_delete",
    ),
    path("sessions/<int:pk>/buy/", views.buy_ticket, name="buy_ticket"),
    # залы
    path("halls/<int:pk>/", views.HallDetailView.as_view(), name="hall_detail"),
]
