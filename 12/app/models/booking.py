"""Модель бронирования (таблица bookings)."""
from __future__ import annotations

import enum
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.guest import Guest
    from app.models.room import Room


class BookingStatus(str, enum.Enum):
    """Возможные статусы бронирования."""

    ACTIVE = "active"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class Booking(Base):
    """Бронирование номера гостем.

    Поля: id (PK), guest_id (FK → guests.id), room_id (FK → rooms.id),
    check_in, check_out, status, total_price. Связи many-to-one к Guest и Room.
    """

    __tablename__ = "bookings"
    __table_args__ = (
        CheckConstraint("check_out > check_in", name="ck_bookings_dates_order"),
        CheckConstraint("total_price >= 0", name="ck_bookings_total_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    guest_id: Mapped[int] = mapped_column(
        ForeignKey("guests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    room_id: Mapped[int] = mapped_column(
        ForeignKey("rooms.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    check_in: Mapped[date] = mapped_column(Date, nullable=False)
    check_out: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=BookingStatus.ACTIVE.value
    )
    total_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    guest: Mapped["Guest"] = relationship(back_populates="bookings")
    room: Mapped["Room"] = relationship(back_populates="bookings")

    @property
    def nights(self) -> int:
        """Количество ночей проживания."""
        return (self.check_out - self.check_in).days

    def __repr__(self) -> str:
        return (
            f"Booking(id={self.id!r}, guest_id={self.guest_id!r}, room_id={self.room_id!r}, "
            f"{self.check_in!r}..{self.check_out!r}, status={self.status!r})"
        )

    def __str__(self) -> str:
        return (
            f"Бронь #{self.id}: гость={self.guest_id}, номер={self.room_id}, "
            f"{self.check_in} → {self.check_out} ({self.nights} ноч.), "
            f"статус={self.status}, итого={self.total_price} руб."
        )
