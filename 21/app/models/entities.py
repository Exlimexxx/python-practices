"""ORM-модели предметной области «бронирование гостиницы»."""
from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Enum as SAEnum

from app.models.base import Base
from app.models.enums import (
    BookingStatus,
    PaymentMethod,
    PaymentStatus,
    RoomStatus,
    RoomType,
    UserRole,
)


def enum_column(enum_cls: type[Enum], name: str) -> SAEnum:
    """Колонка-перечисление с проверкой значений на уровне БД."""
    return SAEnum(
        enum_cls,
        name=name,
        native_enum=False,
        length=32,
        values_callable=lambda cls: [member.value for member in cls],
    )


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    """Пользователь системы: гость (USER) или сотрудник отеля (ADMIN)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        enum_column(UserRole, "user_role"), nullable=False, default=UserRole.USER
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    bookings: Mapped[list[Booking]] = relationship(back_populates="user")

    def __repr__(self) -> str:  # pragma: no cover - отладочное представление
        return f"User(id={self.id!r}, email={self.email!r}, role={self.role.value!r})"


class Room(Base):
    """Гостиничный номер."""

    __tablename__ = "rooms"
    __table_args__ = (
        CheckConstraint("capacity > 0", name="ck_rooms_capacity_positive"),
        CheckConstraint("price_per_night > 0", name="ck_rooms_price_positive"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    number: Mapped[str] = mapped_column(String(16), nullable=False, unique=True, index=True)
    room_type: Mapped[RoomType] = mapped_column(
        enum_column(RoomType, "room_type"), nullable=False, default=RoomType.STANDARD
    )
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    price_per_night: Mapped[float] = mapped_column(Float, nullable=False)
    floor: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[RoomStatus] = mapped_column(
        enum_column(RoomStatus, "room_status"), nullable=False, default=RoomStatus.AVAILABLE
    )
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    bookings: Mapped[list[Booking]] = relationship(back_populates="room")

    def __repr__(self) -> str:  # pragma: no cover - отладочное представление
        return f"Room(id={self.id!r}, number={self.number!r}, status={self.status.value!r})"


class Booking(Base):
    """Бронирование номера гостем на период [check_in, check_out)."""

    __tablename__ = "bookings"
    __table_args__ = (
        CheckConstraint("check_out > check_in", name="ck_bookings_period"),
        CheckConstraint("nights > 0", name="ck_bookings_nights_positive"),
        CheckConstraint("price_total >= 0", name="ck_bookings_price_non_negative"),
        Index("ix_bookings_room_period", "room_id", "check_in", "check_out"),
        Index("ix_bookings_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    room_id: Mapped[int] = mapped_column(
        ForeignKey("rooms.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    check_in: Mapped[date] = mapped_column(Date, nullable=False)
    check_out: Mapped[date] = mapped_column(Date, nullable=False)
    nights: Mapped[int] = mapped_column(Integer, nullable=False)
    price_total: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[BookingStatus] = mapped_column(
        enum_column(BookingStatus, "booking_status"),
        nullable=False,
        default=BookingStatus.CONFIRMED,
    )
    comment: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    user: Mapped[User] = relationship(back_populates="bookings")
    room: Mapped[Room] = relationship(back_populates="bookings")
    payments: Mapped[list[Payment]] = relationship(
        back_populates="booking", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover - отладочное представление
        return (
            f"Booking(id={self.id!r}, room_id={self.room_id!r}, "
            f"{self.check_in!s}..{self.check_out!s}, status={self.status.value!r})"
        )


class Payment(Base):
    """Платёж по бронированию."""

    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_payments_amount_positive"),
        Index("ix_payments_booking", "booking_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    booking_id: Mapped[int] = mapped_column(
        ForeignKey("bookings.id", ondelete="RESTRICT"), nullable=False
    )
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    method: Mapped[PaymentMethod] = mapped_column(
        enum_column(PaymentMethod, "payment_method"), nullable=False, default=PaymentMethod.CARD
    )
    status: Mapped[PaymentStatus] = mapped_column(
        enum_column(PaymentStatus, "payment_status"), nullable=False, default=PaymentStatus.PAID
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    booking: Mapped[Booking] = relationship(back_populates="payments")

    def __repr__(self) -> str:  # pragma: no cover - отладочное представление
        return f"Payment(id={self.id!r}, booking_id={self.booking_id!r}, amount={self.amount!r})"
