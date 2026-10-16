"""Репозиторий гостей: CRUD, поиск по нескольким атрибутам, сортировка."""
from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions import DuplicateError, ValidationError
from app.models.guest import Guest
from app.repositories.base import BaseRepository


class GuestRepository(BaseRepository[Guest]):
    """Операции доступа к данным таблицы guests."""

    model = Guest

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def create(self, full_name: str, email: str, phone: str) -> Guest:
        """Создать гостя с проверкой входных данных и уникальности email.

        :raises ValidationError: если обязательное поле пустое.
        :raises DuplicateError: если email уже занят (UNIQUE-ограничение).
        """
        full_name = (full_name or "").strip()
        email = (email or "").strip().lower()
        phone = (phone or "").strip()
        if not full_name:
            raise ValidationError("ФИО гостя не может быть пустым")
        if "@" not in email:
            raise ValidationError("Некорректный email: " + repr(email))
        if not phone:
            raise ValidationError("Телефон не может быть пустым")

        guest = Guest(full_name=full_name, email=email, phone=phone)
        self.session.add(guest)
        try:
            self.session.flush()
        except IntegrityError as exc:
            self.session.rollback()
            raise DuplicateError("Гость с email " + repr(email) + " уже существует") from exc
        return guest

    def get_by_email(self, email: str) -> Guest | None:
        """Найти гостя по точному email (без учёта регистра)."""
        normalized = (email or "").strip().lower()
        return self.session.scalar(select(Guest).where(Guest.email == normalized))

    def search(
        self,
        full_name: str | None = None,
        phone: str | None = None,
        email: str | None = None,
    ) -> list[Guest]:
        """Поиск по нескольким атрибутам одновременно (условия объединяются AND).

        Внутри каждого атрибута используется частичное совпадение.
        """
        stmt = select(Guest)
        conditions = []
        if full_name:
            conditions.append(Guest.full_name.ilike("%" + full_name.strip() + "%"))
        if phone:
            conditions.append(Guest.phone.ilike("%" + phone.strip() + "%"))
        if email:
            conditions.append(Guest.email.ilike("%" + email.strip() + "%"))
        if conditions:
            stmt = stmt.where(*conditions)
        stmt = stmt.order_by(Guest.full_name)
        return list(self.session.scalars(stmt).all())

    def list_sorted(self, descending: bool = False) -> list[Guest]:
        """Список гостей, отсортированный по ФИО."""
        order = Guest.full_name.desc() if descending else Guest.full_name.asc()
        return list(self.session.scalars(select(Guest).order_by(order)).all())

    def update_guest(
        self,
        guest: Guest,
        full_name: str | None = None,
        email: str | None = None,
        phone: str | None = None,
    ) -> Guest:
        """Изменить данные гостя, проверяя уникальность email."""
        payload: dict[str, object] = {}
        if full_name is not None:
            payload["full_name"] = full_name.strip()
        if email is not None:
            payload["email"] = email.strip().lower()
        if phone is not None:
            payload["phone"] = phone.strip()
        try:
            self.update(guest, **payload)
        except IntegrityError as exc:
            self.session.rollback()
            raise DuplicateError("Не удалось изменить гостя: email уже используется") from exc
        return guest

    def find_by_name_or_email(self, query: str) -> list[Guest]:
        """Поиск OR-условием: совпадение в ФИО ИЛИ в email."""
        pattern = "%" + (query or "").strip() + "%"
        stmt = select(Guest).where(
            or_(Guest.full_name.ilike(pattern), Guest.email.ilike(pattern))
        )
        return list(self.session.scalars(stmt.order_by(Guest.id)).all())
