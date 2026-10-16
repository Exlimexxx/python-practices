"""Схема сводного отчёта по гостинице."""
from __future__ import annotations

from pydantic import BaseModel


class ReportSummary(BaseModel):
    total_users: int
    total_rooms: int
    available_rooms: int
    total_bookings: int
    confirmed_bookings: int
    cancelled_bookings: int
    completed_bookings: int
    active_bookings: int
    total_payments: int
    revenue_total: float
    refunded_total: float
    average_booking_price: float
    average_nights: float
    most_popular_room_type: str | None
