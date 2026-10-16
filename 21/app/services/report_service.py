"""Сервис сводной статистики: агрегирует номера, бронирования и платежи."""
from __future__ import annotations

from app.repositories.booking_repository import BookingRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.room_repository import RoomRepository
from app.repositories.user_repository import UserRepository
from app.schemas.report import ReportSummary


class ReportService:
    """Сводный отчёт по гостинице."""

    def __init__(
        self,
        users: UserRepository,
        rooms: RoomRepository,
        bookings: BookingRepository,
        payments: PaymentRepository,
    ) -> None:
        self.users = users
        self.rooms = rooms
        self.bookings = bookings
        self.payments = payments

    def summary(self) -> ReportSummary:
        room_counts = self.rooms.status_counts()
        booking_counts = self.bookings.status_counts()
        aggregates = self.bookings.aggregates()
        payment_totals = self.payments.totals()
        return ReportSummary(
            total_users=self.users.count(),
            total_rooms=sum(room_counts.values()),
            available_rooms=room_counts.get("available", 0),
            total_bookings=aggregates["total"],
            confirmed_bookings=booking_counts.get("confirmed", 0),
            cancelled_bookings=booking_counts.get("cancelled", 0),
            completed_bookings=booking_counts.get("completed", 0),
            active_bookings=booking_counts.get("confirmed", 0),
            total_payments=self.payments.count(),
            revenue_total=payment_totals.get("paid", 0.0),
            refunded_total=payment_totals.get("refunded", 0.0),
            average_booking_price=aggregates["average_price"],
            average_nights=aggregates["average_nights"],
            most_popular_room_type=self.bookings.most_popular_room_type(),
        )
