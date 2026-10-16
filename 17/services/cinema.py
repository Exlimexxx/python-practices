"""Бизнес-логика кинотеатра отделена от Telegram-обработчиков."""
from __future__ import annotations

from typing import Any
from database.repository import CinemaRepository


class CinemaService:
    def __init__(self, repository: CinemaRepository) -> None:
        self.repository = repository

    def movies(self) -> list[dict[str, Any]]:
        return self.repository.list_movies()

    def movie(self, movie_id: int) -> dict[str, Any]:
        movie = self.repository.get_movie(movie_id)
        if movie is None:
            raise LookupError("Фильм не найден")
        return movie

    def search(self, query: str = "", genre: str = "") -> list[dict[str, Any]]:
        return self.repository.search_movies(query, genre)

    def add_movie(self, title: str, genre: str, duration: int, rating: float) -> int:
        return self.repository.add_movie(title, genre, duration, rating)

    def update_movie(self, movie_id: int, title: str, genre: str, duration: int, rating: float) -> None:
        if not self.repository.update_movie(movie_id, title, genre, duration, rating):
            raise LookupError("Фильм не найден")

    def delete_movie(self, movie_id: int) -> None:
        if not self.repository.delete_movie(movie_id):
            raise LookupError("Фильм не найден")

    def schedule(self) -> list[dict[str, Any]]:
        return self.repository.list_screenings()

    def book(self, screening_id: int, row: int, seat: int, user_id: int) -> int:
        if user_id <= 0:
            raise ValueError("Некорректный идентификатор пользователя")
        return self.repository.book_ticket(screening_id, row, seat, user_id)

    def cancel(self, ticket_id: int, user_id: int) -> None:
        if not self.repository.cancel_ticket(ticket_id, user_id):
            raise LookupError("Билет не найден или принадлежит другому пользователю")
