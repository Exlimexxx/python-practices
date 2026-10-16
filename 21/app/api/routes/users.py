"""Маршруты управления пользователями (только администратор)."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import AdminUser, UserServiceDep
from app.schemas.common import ErrorResponse, Page
from app.schemas.user import AdminUserCreate, UserOut

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "",
    response_model=Page[UserOut],
    summary="Список пользователей",
    description="Доступно только администратору отеля.",
    responses={403: {"model": ErrorResponse, "description": "Недостаточно прав"}},
)
def list_users(
    service: UserServiceDep,
    _: AdminUser,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[UserOut]:
    return service.list_users(limit=limit, offset=offset)


@router.post(
    "",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Создание пользователя администратором",
    description="Позволяет задать роль (USER или ADMIN) и признак активности.",
    responses={
        403: {"model": ErrorResponse, "description": "Недостаточно прав"},
        409: {"model": ErrorResponse, "description": "Email уже зарегистрирован"},
    },
)
def create_user(payload: AdminUserCreate, service: UserServiceDep, _: AdminUser) -> UserOut:
    return service.create_by_admin(payload)


@router.get(
    "/{user_id}",
    response_model=UserOut,
    summary="Получить пользователя по идентификатору",
    responses={404: {"model": ErrorResponse, "description": "Пользователь не найден"}},
)
def get_user(user_id: int, service: UserServiceDep, _: AdminUser) -> UserOut:
    return service.get_user(user_id)
