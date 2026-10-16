"""Репозиторий пользователей."""
from __future__ import annotations

from sqlalchemy import func, select

from app.models import User
from app.repositories.base import SqlAlchemyRepository


class UserRepository(SqlAlchemyRepository[User]):
    model = User

    def get_by_email(self, email: str) -> User | None:
        statement = select(User).where(func.lower(User.email) == email.strip().lower())
        return self.session.scalars(statement).first()

    def search(self, *, limit: int = 100, offset: int = 0) -> list[User]:
        statement = select(User).order_by(User.id).limit(limit).offset(offset)
        return list(self.session.scalars(statement).all())
