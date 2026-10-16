"""Маршруты регистрации и авторизации."""
from __future__ import annotations

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, UserServiceDep
from app.schemas.common import ErrorResponse
from app.schemas.user import TokenResponse, UserLogin, UserOut, UserRegister

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация гостя",
    description="Создаёт пользователя с ролью USER. Email должен быть уникальным.",
    responses={
        409: {"model": ErrorResponse, "description": "Email уже зарегистрирован"},
        422: {"model": ErrorResponse, "description": "Некорректные данные"},
    },
)
def register(payload: UserRegister, service: UserServiceDep) -> UserOut:
    return service.register(payload)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Вход в систему",
    description="Проверяет пару email/пароль и возвращает JWT-токен доступа.",
    responses={401: {"model": ErrorResponse, "description": "Неверные учётные данные"}},
)
def login(payload: UserLogin, service: UserServiceDep) -> TokenResponse:
    return service.login(payload.email, payload.password)


@router.get("/me", response_model=UserOut, summary="Текущий пользователь")
def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)
