"""Автоматические тесты приложения «Кинотеатр» (Django TestCase)."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .exceptions import SeatAlreadyTakenError, SeatOutOfHallError
from .models import Genre, Hall, Movie, Session, Ticket
from .services import book_ticket, safe_book_ticket


class BaseDataMixin:
    """Общие тестовые данные для нескольких классов тестов."""

    @classmethod
    def create_base_data(cls) -> None:
        cls.genre_action = Genre.objects.create(name="Боевик", slug="action")
        cls.genre_drama = Genre.objects.create(name="Драма", slug="drama")
        cls.hall_big = Hall.objects.create(name="Красный", rows=5, seats_per_row=6)
        cls.hall_small = Hall.objects.create(name="Синий", rows=3, seats_per_row=4)
        cls.now = timezone.now().replace(minute=0, second=0, microsecond=0)
        cls.movie_one = Movie.objects.create(
            title="Матрица",
            year=1999,
            rating=Decimal("9.0"),
            duration_minutes=120,
            description="Классика фантастики",
        )
        cls.movie_one.genres.set([cls.genre_action])
        cls.movie_two = Movie.objects.create(
            title="Драма о жизни",
            year=2015,
            rating=Decimal("7.5"),
            duration_minutes=90,
        )
        cls.movie_two.genres.set([cls.genre_drama])
        cls.session_one = Session.objects.create(
            movie=cls.movie_one,
            hall=cls.hall_big,
            start_time=cls.now + timedelta(hours=2),
            price=Decimal("400.00"),
        )
        cls.session_two = Session.objects.create(
            movie=cls.movie_two,
            hall=cls.hall_small,
            start_time=cls.now + timedelta(hours=5),
            price=Decimal("250.00"),
        )


# --------------------------------------------------------------------------
# Тесты моделей
# --------------------------------------------------------------------------
class ModelTests(BaseDataMixin, TestCase):
    """Тесты моделей, связей и валидации."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.create_base_data()

    def test_movie_str(self) -> None:
        self.assertEqual(str(self.movie_one), "Матрица (1999)")

    def test_movie_genres_many_to_many(self) -> None:
        self.assertEqual(self.movie_one.genres.count(), 1)
        self.assertIn(self.movie_one, self.genre_action.movies.all())

    def test_movie_genres_text(self) -> None:
        self.assertEqual(self.movie_one.genres_text, "Боевик")

    def test_hall_capacity(self) -> None:
        self.assertEqual(self.hall_big.capacity, 30)

    def test_session_end_time(self) -> None:
        expected = self.session_one.start_time + timedelta(minutes=120)
        self.assertEqual(self.session_one.end_time, expected)

    def test_session_related_fields(self) -> None:
        self.assertEqual(self.session_one.movie, self.movie_one)
        self.assertEqual(self.session_one.hall, self.hall_big)
        self.assertEqual(self.movie_one.sessions.count(), 1)

    def test_session_overlap_validation(self) -> None:
        conflict = Session(
            movie=self.movie_two,
            hall=self.hall_big,
            start_time=self.session_one.start_time + timedelta(minutes=30),
            price=Decimal("300.00"),
        )
        with self.assertRaises(ValidationError):
            conflict.full_clean()

    def test_session_no_overlap_in_other_hall(self) -> None:
        other = Session(
            movie=self.movie_two,
            hall=self.hall_small,
            start_time=self.session_one.start_time + timedelta(minutes=30),
            price=Decimal("300.00"),
        )
        other.full_clean()  # исключения быть не должно

    def test_movie_clean_requires_title(self) -> None:
        movie = Movie(
            title="   ",
            year=2020,
            rating=Decimal("5.0"),
            duration_minutes=100,
        )
        with self.assertRaises(ValidationError):
            movie.full_clean()

    def test_movie_clean_year_in_future(self) -> None:
        movie = Movie(
            title="Фильм будущего",
            year=timezone.now().year + 10,
            rating=Decimal("5.0"),
            duration_minutes=100,
        )
        with self.assertRaises(ValidationError):
            movie.full_clean()

    def test_movie_rating_validator(self) -> None:
        movie = Movie(
            title="Плохой рейтинг",
            year=2020,
            rating=Decimal("15.0"),
            duration_minutes=100,
        )
        with self.assertRaises(ValidationError):
            movie.full_clean()

    def test_ticket_clean_row_bounds(self) -> None:
        ticket = Ticket(
            session=self.session_one,
            row=99,
            seat=1,
            price=Decimal("100.00"),
            buyer_name="Иванов Иван",
        )
        with self.assertRaises(ValidationError):
            ticket.full_clean()

    def test_ticket_unique_seat_constraint(self) -> None:
        Ticket.objects.create(
            session=self.session_one,
            row=1,
            seat=1,
            price=Decimal("100.00"),
            buyer_name="Первый",
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Ticket.objects.create(
                    session=self.session_one,
                    row=1,
                    seat=1,
                    price=Decimal("100.00"),
                    buyer_name="Второй",
                )

    def test_session_revenue_aggregate(self) -> None:
        Ticket.objects.create(
            session=self.session_two, row=1, seat=1,
            price=Decimal("250.00"), buyer_name="Тест",
        )
        Ticket.objects.create(
            session=self.session_two, row=1, seat=2,
            price=Decimal("250.00"), buyer_name="Тест 2",
        )
        self.assertEqual(self.session_two.revenue, Decimal("500.00"))

    def test_session_free_seats(self) -> None:
        Ticket.objects.create(
            session=self.session_two, row=1, seat=1,
            price=Decimal("250.00"), buyer_name="Тест",
        )
        self.assertEqual(self.session_two.free_seats, self.hall_small.capacity - 1)


# --------------------------------------------------------------------------
# Тесты сервисного слоя (собственные исключения)
# --------------------------------------------------------------------------
class ServiceTests(BaseDataMixin, TestCase):
    """Тесты продажи билетов и собственной иерархии исключений."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.create_base_data()

    def test_book_ticket_success(self) -> None:
        ticket = book_ticket(self.session_one, 1, 2, "Петров Пётр")
        self.assertEqual(ticket.price, self.session_one.price)
        self.assertEqual(self.session_one.tickets.count(), 1)

    def test_book_ticket_out_of_hall(self) -> None:
        with self.assertRaises(SeatOutOfHallError):
            book_ticket(self.session_one, 50, 1, "Петров Пётр")

    def test_book_ticket_duplicate(self) -> None:
        book_ticket(self.session_one, 2, 2, "Первый")
        with self.assertRaises(SeatAlreadyTakenError):
            book_ticket(self.session_one, 2, 2, "Второй")

    def test_safe_book_ticket_returns_error_text(self) -> None:
        result = safe_book_ticket(self.session_one, 99, 99, "Тест")
        self.assertTrue(result.startswith("ОШИБКА"))
        self.assertEqual(Ticket.objects.count(), 0)


# --------------------------------------------------------------------------
# Тесты представлений
# --------------------------------------------------------------------------
class PublicViewTests(BaseDataMixin, TestCase):
    """Тесты доступных без входа страниц."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.create_base_data()
        for index in range(12):
            movie = Movie.objects.create(
                title=f"Фильм {index:02d}",
                year=2000 + index,
                rating=Decimal("5.0") + Decimal(index) / 10,
                duration_minutes=80 + index,
            )
            movie.genres.set([cls.genre_drama])

    def test_index_page(self) -> None:
        response = self.client.get(reverse("cinema:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Кинотеатр")

    def test_statistics_page(self) -> None:
        response = self.client.get(reverse("cinema:statistics"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Статистика")

    def test_genre_list_page(self) -> None:
        response = self.client.get(reverse("cinema:genre_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Боевик")

    def test_movie_list_page(self) -> None:
        response = self.client.get(reverse("cinema:movie_list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "cinema/movie_list.html")

    def test_movie_list_search(self) -> None:
        response = self.client.get(reverse("cinema:movie_list"), {"q": "Матрица"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Матрица")
        self.assertNotIn(response.context["movies"], [])

    def test_movie_list_search_no_results(self) -> None:
        response = self.client.get(reverse("cinema:movie_list"), {"q": "нетакого"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["movies"]), 0)

    def test_movie_list_filter_by_genre(self) -> None:
        response = self.client.get(
            reverse("cinema:movie_list"), {"genre": self.genre_action.pk}
        )
        self.assertEqual(response.status_code, 200)
        titles = [m.title for m in response.context["movies"]]
        self.assertIn("Матрица", titles)
        self.assertNotIn("Драма о жизни", titles)

    def test_movie_list_filter_by_year(self) -> None:
        response = self.client.get(reverse("cinema:movie_list"), {"year_from": 2005})
        self.assertEqual(response.status_code, 200)
        for movie in response.context["movies"]:
            self.assertGreaterEqual(movie.year, 2005)

    def test_movie_list_filter_by_rating(self) -> None:
        response = self.client.get(reverse("cinema:movie_list"), {"min_rating": "9.0"})
        self.assertEqual(response.status_code, 200)
        for movie in response.context["movies"]:
            self.assertGreaterEqual(movie.rating, Decimal("9.0"))

    def test_movie_list_sorting_ascending(self) -> None:
        response = self.client.get(reverse("cinema:movie_list"), {"sort": "title"})
        titles = [m.title for m in response.context["movies"]]
        self.assertEqual(titles, sorted(titles))

    def test_movie_list_pagination(self) -> None:
        response = self.client.get(reverse("cinema:movie_list"))
        self.assertEqual(len(response.context["movies"]), 10)
        self.assertTrue(response.context["is_paginated"])
        second = self.client.get(reverse("cinema:movie_list"), {"page": 2})
        self.assertEqual(second.status_code, 200)
        self.assertEqual(len(second.context["movies"]), 4)

    def test_movie_detail_page(self) -> None:
        response = self.client.get(
            reverse("cinema:movie_detail", args=[self.movie_one.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Матрица")

    def test_movie_detail_404(self) -> None:
        response = self.client.get(reverse("cinema:movie_detail", args=[99999]))
        self.assertEqual(response.status_code, 404)

    def test_session_list_filter_by_hall(self) -> None:
        response = self.client.get(
            reverse("cinema:session_list"), {"hall": self.hall_big.pk}
        )
        self.assertEqual(response.status_code, 200)
        for session in response.context["sessions"]:
            self.assertEqual(session.hall, self.hall_big)

    def test_session_list_sorting_by_price(self) -> None:
        response = self.client.get(reverse("cinema:session_list"), {"sort": "-price"})
        prices = [s.price for s in response.context["sessions"]]
        self.assertEqual(prices, sorted(prices, reverse=True))

    def test_session_detail_page(self) -> None:
        response = self.client.get(
            reverse("cinema:session_detail", args=[self.session_one.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Красный")

    @override_settings(DEBUG=False)
    def test_custom_404_handler(self) -> None:
        response = self.client.get("/no-such-address/")
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, "cinema/404.html")


# --------------------------------------------------------------------------
# Тесты аутентификации и разграничения доступа
# --------------------------------------------------------------------------
class AuthAndPermissionTests(BaseDataMixin, TestCase):
    """Тесты входа, прав обычного пользователя и администратора."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.create_base_data()
        cls.staff = User.objects.create_user(
            username="admin16", password="SuperPass123", is_staff=True
        )
        cls.simple = User.objects.create_user(
            username="user16", password="UserPass123"
        )

    def test_login_page_available(self) -> None:
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "registration/login.html")

    def test_login_success(self) -> None:
        ok = self.client.login(username="user16", password="UserPass123")
        self.assertTrue(ok)
        response = self.client.get(reverse("cinema:index"))
        self.assertContains(response, "user16")

    def test_create_redirects_anonymous_to_login(self) -> None:
        response = self.client.get(reverse("cinema:movie_create"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_create_forbidden_for_regular_user(self) -> None:
        self.client.login(username="user16", password="UserPass123")
        response = self.client.get(reverse("cinema:movie_create"))
        self.assertEqual(response.status_code, 403)

    def test_create_allowed_for_staff(self) -> None:
        self.client.login(username="admin16", password="SuperPass123")
        response = self.client.get(reverse("cinema:movie_create"))
        self.assertEqual(response.status_code, 200)
        response = self.client.post(
            reverse("cinema:movie_create"),
            {
                "title": "Новый фильм",
                "genres": [self.genre_action.pk],
                "year": 2020,
                "rating": "8.0",
                "description": "Описание",
                "duration_minutes": 100,
                "is_active": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Movie.objects.filter(title="Новый фильм").exists())

    def test_create_form_validation_rejects_duplicate_title(self) -> None:
        self.client.login(username="admin16", password="SuperPass123")
        response = self.client.post(
            reverse("cinema:movie_create"),
            {
                "title": "Матрица",
                "genres": [self.genre_action.pk],
                "year": 2020,
                "rating": "8.0",
                "description": "",
                "duration_minutes": 100,
            },
        )
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertFalse(form.is_valid())
        self.assertIn(
            "Фильм с таким названием уже добавлен.", form.errors["title"]
        )

    def test_update_allowed_for_staff(self) -> None:
        self.client.login(username="admin16", password="SuperPass123")
        response = self.client.post(
            reverse("cinema:movie_update", args=[self.movie_one.pk]),
            {
                "title": "Матрица (режиссёрская версия)",
                "genres": [self.genre_action.pk],
                "year": 1999,
                "rating": "9.5",
                "description": "Обновлено",
                "duration_minutes": 136,
                "is_active": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.movie_one.refresh_from_db()
        self.assertEqual(self.movie_one.rating, Decimal("9.5"))

    def test_delete_forbidden_for_regular_user(self) -> None:
        self.client.login(username="user16", password="UserPass123")
        response = self.client.get(
            reverse("cinema:movie_delete", args=[self.movie_one.pk])
        )
        self.assertEqual(response.status_code, 403)

    def test_delete_allowed_for_staff(self) -> None:
        movie = Movie.objects.create(
            title="Фильм без сеансов",
            year=2021,
            rating=Decimal("6.0"),
            duration_minutes=95,
        )
        self.client.login(username="admin16", password="SuperPass123")
        response = self.client.post(reverse("cinema:movie_delete", args=[movie.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Movie.objects.filter(pk=movie.pk).exists())

    def test_delete_protected_movie_shows_error(self) -> None:
        """Фильм с сеансами защищён связью PROTECT и не удаляется."""
        self.client.login(username="admin16", password="SuperPass123")
        response = self.client.post(
            reverse("cinema:movie_delete", args=[self.movie_one.pk]), follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Movie.objects.filter(pk=self.movie_one.pk).exists())
        self.assertContains(response, "с ним связаны сеансы")

    def test_session_create_forbidden_for_regular_user(self) -> None:
        self.client.login(username="user16", password="UserPass123")
        response = self.client.get(reverse("cinema:session_create"))
        self.assertEqual(response.status_code, 403)

    def test_buy_ticket_requires_login(self) -> None:
        response = self.client.post(
            reverse("cinema:buy_ticket", args=[self.session_one.pk]),
            {"row": 1, "seat": 1, "buyer_name": "Гость"},
        )
        self.assertEqual(response.status_code, 302)

    def test_buy_ticket_success(self) -> None:
        self.client.login(username="user16", password="UserPass123")
        response = self.client.post(
            reverse("cinema:buy_ticket", args=[self.session_one.pk]),
            {"row": 3, "seat": 4, "buyer_name": "Сидоров Сидор", "is_paid": "on"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Ticket.objects.filter(session=self.session_one, row=3, seat=4).exists()
        )

    def test_buy_ticket_second_time_error(self) -> None:
        self.client.login(username="user16", password="UserPass123")
        payload = {"row": 2, "seat": 3, "buyer_name": "Сидоров Сидор"}
        self.client.post(reverse("cinema:buy_ticket", args=[self.session_one.pk]), payload)
        response = self.client.post(
            reverse("cinema:buy_ticket", args=[self.session_one.pk]), payload, follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            Ticket.objects.filter(session=self.session_one, row=2, seat=3).count(), 1
        )

    def test_orm_demo_requires_login(self) -> None:
        response = self.client.get(reverse("cinema:orm_demo"))
        self.assertEqual(response.status_code, 302)
        self.client.login(username="user16", password="UserPass123")
        response = self.client.get(reverse("cinema:orm_demo"))
        self.assertEqual(response.status_code, 200)


# --------------------------------------------------------------------------
# Тесты административной панели
# --------------------------------------------------------------------------
class AdminTests(BaseDataMixin, TestCase):
    """Тесты регистрации моделей и настроек Admin."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.create_base_data()
        cls.staff = User.objects.create_superuser(
            username="super16", password="SuperPass123", email="a@b.c"
        )

    def test_admin_login_and_movie_changelist(self) -> None:
        self.client.login(username="super16", password="SuperPass123")
        response = self.client.get("/admin/cinema/movie/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Матрица")

    def test_admin_genre_changelist(self) -> None:
        self.client.login(username="super16", password="SuperPass123")
        response = self.client.get("/admin/cinema/genre/")
        self.assertEqual(response.status_code, 200)

    def test_admin_session_changelist(self) -> None:
        self.client.login(username="super16", password="SuperPass123")
        response = self.client.get("/admin/cinema/session/")
        self.assertEqual(response.status_code, 200)

    def test_admin_ticket_changelist(self) -> None:
        self.client.login(username="super16", password="SuperPass123")
        response = self.client.get("/admin/cinema/ticket/")
        self.assertEqual(response.status_code, 200)

    def test_admin_requires_authorization(self) -> None:
        response = self.client.get("/admin/cinema/movie/")
        self.assertEqual(response.status_code, 302)
