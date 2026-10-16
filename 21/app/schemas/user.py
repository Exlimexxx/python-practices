"""Схемы пользователей, регистрации и авторизации."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import UserRole

PASSWORD_MIN_LENGTH = 8


class UserRegister(BaseModel):
    """Регистрация гостя: роль всегда USER."""

    email: EmailStr
    full_name: str = Field(min_length=2, max_length=120, examples=["Иван Петров"])
    password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=128)


class AdminUserCreate(UserRegister):
    """Создание пользователя администратором: допускается выбор роли."""

    role: UserRole = UserRole.USER
    is_active: bool = True


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Срок жизни токена в секундах")
    role: UserRole


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
