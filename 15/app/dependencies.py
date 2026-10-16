"""Провайдер сервисов для обработчиков Flask (внедрение зависимостей)."""
from __future__ import annotations

from dataclasses import dataclass

from flask import g

from app.services import BookingService, GuestService, RoomService


@dataclass
class Services:
    """Набор сервисов, разделяющих одну сессию текущего запроса."""

    rooms: RoomService
    guests: GuestService
    bookings: BookingService


def get_services() -> Services:
    """Возвращает сервисы, привязанные к сессии текущего HTTP-запроса."""
    cached = getattr(g, "services", None)
    if cached is None:
        session = g.db_session
        cached = Services(
            rooms=RoomService(session),
            guests=GuestService(session),
            bookings=BookingService(session),
        )
        g.services = cached
    return cached
