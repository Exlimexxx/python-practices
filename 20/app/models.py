"""SQLAlchemy ORM-модель бронирования гостиницы."""
from __future__ import annotations
from datetime import date
from sqlalchemy import CheckConstraint, Date, Float, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        CheckConstraint("price_total >= 0", name="ck_booking_price_nonnegative"),
        CheckConstraint("check_out > check_in", name="ck_booking_dates_order"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    room_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    guest_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    guest_name: Mapped[str] = mapped_column(String(120), nullable=False)
    guest_email: Mapped[str] = mapped_column(String(160), nullable=False)
    check_in: Mapped[date] = mapped_column(Date, nullable=False)
    check_out: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="confirmed")
    price_total: Mapped[float] = mapped_column(Float, nullable=False)
