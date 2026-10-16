"""Сервис пользователей: регистрация, аутентификация, выдача токенов."""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.config import Settings
from app.exceptions import (
    AuthenticationError,
    EmailAlreadyUsedError,
    UserNotFoundError,
)
from app.models import User, UserRole
from app.repositories.user_repository import UserRepository
from app.schemas.common import Page
from app.schemas.user import AdminUserCreate, TokenResponse, UserOut, UserRegister
from app.security import create_access_token, hash_password, verify_password

logger = logging.getLogger(__name__)


def to_user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
    )


class UserService:
    """Регистрация и идентификация пользователей."""

    def __init__(self, session: Session, users: UserRepository, settings: Settings) -> None:
        self.session = session
        self.users = users
        self.settings = settings

    def register(
        self,
        payload: UserRegister,
        *,
        role: UserRole = UserRole.USER,
        is_active: bool = True,
    ) -> UserOut:
        email = payload.email.strip().lower()
        if self.users.get_by_email(email) is not None:
            raise EmailAlreadyUsedError(
                f"Пользователь с email {email} уже зарегистрирован",
                details={"email": email},
            )
        user = User(
            email=email,
            full_name=payload.full_name.strip(),
            password_hash=hash_password(payload.password),
            role=role,
            is_active=is_active,
        )
        self.users.add(user)
        self.session.commit()
        logger.info("Зарегистрирован пользователь id=%s role=%s", user.id, user.role.value)
        return to_user_out(user)

    def create_by_admin(self, payload: AdminUserCreate) -> UserOut:
        return self.register(payload, role=payload.role, is_active=payload.is_active)

    def authenticate(self, email: str, password: str) -> User:
        user = self.users.get_by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            raise AuthenticationError("Неверный email или пароль")
        if not user.is_active:
            raise AuthenticationError("Учётная запись отключена")
        return user

    def issue_token(self, user: User) -> TokenResponse:
        token, expires_in = create_access_token(
            user.id, role=user.role.value, settings=self.settings
        )
        return TokenResponse(access_token=token, expires_in=expires_in, role=user.role)

    def login(self, email: str, password: str) -> TokenResponse:
        return self.issue_token(self.authenticate(email, password))

    def get_entity(self, user_id: int) -> User:
        user = self.users.get(user_id)
        if user is None:
            raise UserNotFoundError(
                f"Пользователь с id {user_id} не найден", details={"user_id": user_id}
            )
        return user

    def get_user(self, user_id: int) -> UserOut:
        return to_user_out(self.get_entity(user_id))

    def list_users(self, *, limit: int = 20, offset: int = 0) -> Page[UserOut]:
        items = self.users.search(limit=limit, offset=offset)
        return Page[UserOut](
            total=self.users.count(),
            limit=limit,
            offset=offset,
            items=[to_user_out(user) for user in items],
        )

    def ensure_admin(self, *, email: str, password: str, full_name: str) -> User | None:
        """Создать администратора из настроек при первом запуске."""
        if not email or not password:
            return None
        existing = self.users.get_by_email(email)
        if existing is not None:
            return existing
        admin = User(
            email=email.strip().lower(),
            full_name=full_name,
            password_hash=hash_password(password),
            role=UserRole.ADMIN,
            is_active=True,
        )
        self.users.add(admin)
        self.session.commit()
        logger.info("Создан администратор по умолчанию: %s", admin.email)
        return admin
