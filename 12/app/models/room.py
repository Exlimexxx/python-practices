"""Модель номера отеля (таблица rooms)."""
from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.booking import Booking


class Room(Base):
    """Номер отеля.

    Поля: id (PK), number (UNIQUE, NOT NULL), room_type, capacity,
    price_per_night, is_active. Связь one-to-many: один номер — много броней.
    """

    __tablename__ = "rooms"
    __table_args__ = (
        CheckConstraint("capacity > 0", name="ck_rooms_capacity_positive"),
        CheckConstraint("price_per_night >= 0", name="ck_rooms_price_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    number: Mapped[str] = mapped_column(String(16), nullable=False, unique=True, index=True)
    room_type: Mapped[str] = mapped_column(String(40), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    price_per_night: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    bookings: Mapped[list["Booking"]] = relationship(
        back_populates="room",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"Room(id={self.id!r}, number={self.number!r}, type={self.room_type!r}, "
            f"price={self.price_per_night!r})"
        )

    def __str__(self) -> str:
        state = "активен" if self.is_active else "неактивен"
        return (
            f"Номер {self.number} ({self.room_type}), мест: {self.capacity}, "
            f"цена: {self.price_per_night} руб./ночь, {state}"
        )
