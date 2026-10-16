"""ORM-модели предметной области отеля: Room, Guest, Booking."""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:  # pragma: no cover - только для аннотаций
    from sqlalchemy.orm import Session


def _utcnow() -> datetime:
    """Текущее время в UTC без микросекунд (для стабильного вывода)."""
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)


#: Допустимые типы номеров отеля.
ROOM_TYPES: tuple[str, ...] = ("Стандарт", "Комфорт", "Люкс", "Апартаменты")
#: Допустимые статусы бронирования.
BOOKING_STATUSES: tuple[str, ...] = ("confirmed", "cancelled")
#: Человекочитаемые названия статусов.
STATUS_LABELS: dict[str, str] = {
    "confirmed": "Подтверждено",
    "cancelled": "Отменено",
}


class Room(Base):
    """Гостиничный номер (сущность «Номер»)."""

    __tablename__ = "rooms"
    __table_args__ = (
        CheckConstraint("capacity > 0", name="ck_rooms_capacity_positive"),
        CheckConstraint("price_per_night >= 0", name="ck_rooms_price_non_negative"),
        UniqueConstraint("number", name="uq_rooms_number"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    number: Mapped[str] = mapped_column(String(10), nullable=False, unique=True)
    room_type: Mapped[str] = mapped_column(String(40), nullable=False, default="Стандарт")
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    price_per_night: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    floor: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)

    bookings: Mapped[list["Booking"]] = relationship(
        "Booking", back_populates="room", cascade="all, delete-orphan"
    )

    def to_dict(self) -> dict[str, Any]:
        """Сериализация номера в JSON-совместимый словарь."""
        return {
            "id": self.id,
            "number": self.number,
            "room_type": self.room_type,
            "capacity": self.capacity,
            "price_per_night": round(self.price_per_night, 2),
            "floor": self.floor,
            "description": self.description,
            "is_active": self.is_active,
            "status_label": "Доступен" if self.is_active else "Закрыт",
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @property
    def title(self) -> str:
        """Короткое название номера для интерфейса."""
        return f"Номер {self.number} ({self.room_type})"

    def __repr__(self) -> str:  # pragma: no cover - отладочное представление
        return f"<Room id={self.id} number={self.number!r} type={self.room_type!r}>"


class Guest(Base):
    """Гость отеля (сущность «Гость»)."""

    __tablename__ = "guests"
    __table_args__ = (UniqueConstraint("email", name="uq_guests_email"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    phone: Mapped[str] = mapped_column(String(30), nullable=False, default="")
    passport: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    city: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)

    bookings: Mapped[list["Booking"]] = relationship(
        "Booking", back_populates="guest", cascade="all, delete-orphan"
    )

    def to_dict(self) -> dict[str, Any]:
        """Сериализация гостя в JSON-совместимый словарь."""
        return {
            "id": self.id,
            "full_name": self.full_name,
            "email": self.email,
            "phone": self.phone,
            "passport": self.passport,
            "city": self.city,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Guest id={self.id} name={self.full_name!r}>"


class Booking(Base):
    """Бронирование номера гостем (сущность «Бронирование»)."""

    __tablename__ = "bookings"
    __table_args__ = (
        CheckConstraint("check_out > check_in", name="ck_bookings_date_order"),
        CheckConstraint("guests_count > 0", name="ck_bookings_guests_positive"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False)
    guest_id: Mapped[int] = mapped_column(ForeignKey("guests.id", ondelete="CASCADE"), nullable=False)
    check_in: Mapped[date] = mapped_column(Date, nullable=False)
    check_out: Mapped[date] = mapped_column(Date, nullable=False)
    guests_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="confirmed")
    total_price: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    comment: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)

    room: Mapped["Room"] = relationship("Room", back_populates="bookings")
    guest: Mapped["Guest"] = relationship("Guest", back_populates="bookings")

    @property
    def nights(self) -> int:
        """Количество ночей бронирования."""
        return max((self.check_out - self.check_in).days, 0)

    @property
    def status_label(self) -> str:
        """Человекочитаемый статус бронирования."""
        return STATUS_LABELS.get(self.status, self.status)

    def to_dict(self, *, with_relations: bool = True) -> dict[str, Any]:
        """Сериализация бронирования в JSON-совместимый словарь."""
        data: dict[str, Any] = {
            "id": self.id,
            "room_id": self.room_id,
            "guest_id": self.guest_id,
            "check_in": self.check_in.isoformat() if self.check_in else None,
            "check_out": self.check_out.isoformat() if self.check_out else None,
            "nights": self.nights,
            "guests_count": self.guests_count,
            "status": self.status,
            "status_label": self.status_label,
            "total_price": round(self.total_price, 2),
            "comment": self.comment,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if with_relations:
            data["room"] = self.room.to_dict() if self.room else None
            data["guest"] = self.guest.to_dict() if self.guest else None
        return data

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<Booking id={self.id} room={self.room_id} guest={self.guest_id} "
            f"{self.check_in}..{self.check_out}>"
        )
