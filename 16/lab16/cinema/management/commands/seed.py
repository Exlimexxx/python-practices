"""Команда заполнения базы тестовыми данными кинотеатра (не менее 20 записей)."""

from __future__ import annotations

import io
import logging
import random
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone

from cinema.models import Genre, Hall, Movie, Session, Ticket

logger = logging.getLogger(__name__)

GENRES = [
    ("Боевик", "boevik", "Динамичные фильмы с погонями и драками."),
    ("Драма", "drama", "Фильмы с выраженным сюжетом и переживаниями героев."),
    ("Комедия", "komediya", "Фильмы, рассчитанные на поднятие настроения."),
    ("Фантастика", "fantastika", "Научная фантастика и космос."),
    ("Триллер", "triller", "Напряжённые фильмы с интригой."),
    ("Анимация", "animaciya", "Мультипликационные фильмы для всей семьи."),
    ("Ужасы", "uzhasy", "Фильмы ужасов и мистика."),
    ("Приключения", "priklyucheniya", "Путешествия и приключенческий сюжет."),
]

HALLS = [
    ("Красный", 10, 12, "Большой зал с Dolby Atmos."),
    ("Синий", 8, 10, "Средний зал с лазерным проектором."),
    ("Зелёный", 6, 8, "Малый зал для камерных показов."),
    ("VIP-зал", 4, 6, "Зал повышенной комфортности с диванами."),
    ("Ремонтный", 5, 5, "Зал закрыт на ремонт (демонстрация фильтра is_active)."),
]

MOVIES = [
    ("Матрица", 1999, "9.2", 136, ["Фантастика", "Боевик"]),
    ("Начало", 2010, "8.9", 148, ["Фантастика", "Триллер"]),
    ("Интерстеллар", 2014, "8.7", 169, ["Фантастика", "Драма", "Приключения"]),
    ("Побег из Шоушенка", 1994, "9.3", 142, ["Драма"]),
    ("Криминальное чтиво", 1994, "8.9", 154, ["Триллер", "Драма"]),
    ("Форрест Гамп", 1994, "8.8", 142, ["Драма", "Комедия"]),
    ("Тёмный рыцарь", 2008, "9.0", 152, ["Боевик", "Триллер"]),
    ("Король Лев", 1994, "8.5", 88, ["Анимация", "Приключения"]),
    ("Гладиатор", 2000, "8.6", 155, ["Боевик", "Драма"]),
    ("Остров проклятых", 2010, "8.6", 138, ["Триллер"]),
    ("Аватар", 2009, "7.9", 162, ["Фантастика", "Приключения"]),
    ("Джокер", 2019, "8.4", 122, ["Драма", "Триллер"]),
    ("Паразиты", 2019, "8.5", 132, ["Драма", "Триллер"]),
    ("Один дома", 1990, "7.6", 103, ["Комедия"]),
    ("Терминатор 2", 1991, "8.5", 137, ["Боевик", "Фантастика"]),
    ("Чужой", 1979, "8.4", 117, ["Ужасы", "Фантастика"]),
    ("Сияние", 1980, "8.3", 146, ["Ужасы", "Триллер"]),
    ("Леон", 1994, "8.5", 110, ["Боевик", "Драма"]),
    ("ВАЛЛ-И", 2008, "8.4", 98, ["Анимация", "Фантастика"]),
    ("Головоломка", 2015, "8.1", 95, ["Анимация", "Комедия"]),
    ("Вверх", 2009, "8.3", 96, ["Анимация", "Приключения"]),
    ("Дюна", 2021, "8.0", 155, ["Фантастика", "Драма"]),
    ("Оппенгеймер", 2023, "8.6", 180, ["Драма"]),
    ("Бойцовский клуб", 1999, "8.8", 139, ["Драма", "Триллер"]),
    ("Зелёная миля", 1999, "9.1", 189, ["Драма", "Фантастика"]),
    ("Отступники", 2006, "8.5", 151, ["Триллер", "Драма"]),
    ("Пираты Карибского моря", 2003, "8.0", 143, ["Приключения", "Комедия"]),
    ("Властелин колец: Братство Кольца", 2001, "8.6", 178, ["Приключения", "Фантастика"]),
    ("Мстители", 2012, "8.0", 143, ["Боевик", "Фантастика"]),
    ("Гарри Поттер и философский камень", 2001, "7.7", 152, ["Приключения", "Фантастика"]),
]

SLOT_HOURS = [10, 14, 18, 21]


def make_poster(number: int, title: str) -> ContentFile:
    """Сгенерировать простую PNG-афишу средствами Pillow."""
    from PIL import Image, ImageDraw

    palette = [(18, 52, 86), (86, 24, 52), (24, 86, 60), (86, 68, 18)]
    color = palette[number % len(palette)]
    image = Image.new("RGB", (200, 300), color)
    draw = ImageDraw.Draw(image)
    draw.rectangle((10, 10, 190, 290), outline=(255, 255, 255), width=2)
    draw.text((18, 20), f"#{number}", fill=(255, 255, 255))
    draw.text((18, 260), title[:28], fill=(255, 255, 255))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return ContentFile(buffer.getvalue(), name=f"poster_{number:02d}.png")


class Command(BaseCommand):
    """Заполнить базу тестовыми данными: жанры, залы, фильмы, сеансы, билеты."""

    help = "Заполняет БД тестовыми данными кинотеатра (вариант 4)."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Удалить существующие данные перед заполнением.",
        )

    def handle(self, *args, **options) -> None:
        random.seed(16)  # воспроизводимость тестовых данных

        if options["clear"]:
            Ticket.objects.all().delete()
            Session.objects.all().delete()
            Movie.objects.all().delete()
            Hall.objects.all().delete()
            Genre.objects.all().delete()
            self.stdout.write("Существующие данные удалены.")

        genres: dict[str, Genre] = {}
        for name, slug, description in GENRES:
            genre, _ = Genre.objects.get_or_create(
                name=name, defaults={"slug": slug, "description": description}
            )
            genres[name] = genre

        halls: dict[str, Hall] = {}
        for name, rows, seats, description in HALLS:
            hall, _ = Hall.objects.get_or_create(
                name=name,
                defaults={
                    "rows": rows,
                    "seats_per_row": seats,
                    "description": description,
                    "is_active": name != "Ремонтный",
                },
            )
            halls[name] = hall

        created_movies = 0
        movies: list[Movie] = []
        for index, (title, year, rating, duration, genre_names) in enumerate(MOVIES, start=1):
            movie, created = Movie.objects.get_or_create(
                title=title,
                defaults={
                    "year": year,
                    "rating": Decimal(rating),
                    "duration_minutes": duration,
                    "description": f"Фильм «{title}» ({year} год). Жанры: "
                    + ", ".join(genre_names)
                    + ".",
                    "is_active": index % 9 != 0,
                },
            )
            movie.genres.set([genres[name] for name in genre_names])
            if created:
                created_movies += 1
                movie.poster.save(
                    f"poster_{index:02d}.png", make_poster(index, title), save=True
                )
            movies.append(movie)

        self.stdout.write(f"Жанров: {Genre.objects.count()}, фильмов создано: {created_movies}")

        active_halls = [h for h in halls.values() if h.is_active]
        now = timezone.localtime()
        start_day = now.date()
        created_sessions = 0
        sessions: list[Session] = []
        for day_offset in range(10):
            day = start_day + timedelta(days=day_offset)
            for slot_index, hour in enumerate(SLOT_HOURS):
                hall = active_halls[slot_index % len(active_halls)]
                movie = movies[(day_offset * len(SLOT_HOURS) + slot_index) % len(movies)]
                naive = datetime.combine(day, time(hour=hour, minute=0))
                start_time = timezone.make_aware(naive, timezone.get_current_timezone())
                price = Decimal("250.00") + Decimal(slot_index * 60) + Decimal(day_offset * 5)
                session = Session.objects.filter(
                    movie=movie, hall=hall, start_time=start_time
                ).first()
                if session is None:
                    session = Session.objects.create(
                        movie=movie,
                        hall=hall,
                        start_time=start_time,
                        price=price,
                        status=Session.Status.PLANNED,
                    )
                    created_sessions += 1
                sessions.append(session)

        self.stdout.write(f"Сеансов создано: {created_sessions}")

        created_tickets = 0
        for index, session in enumerate(sessions):
            tickets_to_sell = index % 4
            for seat_number in range(1, tickets_to_sell + 1):
                row = (seat_number - 1) // session.hall.seats_per_row + 1
                seat = (seat_number - 1) % session.hall.seats_per_row + 1
                _, created = Ticket.objects.get_or_create(
                    session=session,
                    row=row,
                    seat=seat,
                    defaults={
                        "price": session.price,
                        "buyer_name": f"Покупатель {index + 1}-{seat_number}",
                        "is_paid": seat_number % 3 != 0,
                    },
                )
                created_tickets += int(created)

        self.stdout.write(f"Билетов создано: {created_tickets}")
        self.stdout.write(
            self.style.SUCCESS(
                "Итого в базе: "
                f"жанров {Genre.objects.count()}, "
                f"залов {Hall.objects.count()}, "
                f"фильмов {Movie.objects.count()}, "
                f"сеансов {Session.objects.count()}, "
                f"билетов {Ticket.objects.count()}."
            )
        )
        logger.info("Тестовые данные кинотеатра загружены.")
