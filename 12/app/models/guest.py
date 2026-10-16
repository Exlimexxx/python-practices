"""Модель гостя отеля (таблица guests)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.booking import Booking


class Guest(Base):
    """Гость отеля.

    Поля: id (PK), full_name (NOT NULL), email (UNIQUE, NOT NULL), phone (NOT NULL).
    Связь one-to-many: один гость — много бронирований.
    """

    __tablename__ = "guests"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    phone: Mapped[str] = mapped_column(String(32), nullable=False)

    bookings: Mapped[list["Booking"]] = relationship(
        back_populates="guest",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"Guest(id={self.id!r}, full_name={self.full_name!r}, email={self.email!r})"

    def __str__(self) -> str:
        return f"Гость #{self.id}: {self.full_name} (email: {self.email}, тел: {self.phone})"
