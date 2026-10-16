"""Маршруты бронирований."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import AdminUser, BookingServiceDep, CurrentUser
from app.schemas.booking import (
    BookingCancelRequest,
    BookingCreate,
    BookingFilter,
    BookingOut,
    BookingPage,
)
from app.schemas.common import ErrorResponse

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post(
    "",
    response_model=BookingOut,
    status_code=status.HTTP_201_CREATED,
    summary="Создать бронирование",
    description=(
        "Проверяет существование номера, его статус, дату заезда и отсутствие "
        "пересечения с другими подтверждёнными бронированиями. "
        "Стоимость рассчитывается как число ночей × цена за ночь."
    ),
    responses={
        401: {"model": ErrorResponse, "description": "Требуется авторизация"},
        404: {"model": ErrorResponse, "description": "Номер не найден"},
        409: {"model": ErrorResponse, "description": "Номер занят или недоступен"},
        422: {"model": ErrorResponse, "description": "Некорректный период"},
    },
)
def create_booking(
    payload: BookingCreate, service: BookingServiceDep, user: CurrentUser
) -> BookingOut:
    return service.create_booking(payload, user)


@router.get(
    "",
    response_model=BookingPage,
    summary="Список бронирований",
    description=(
        "Гость видит только свои бронирования, администратор — все. "
        "Доступны фильтры по статусу, номеру, гостю и датам, а также сортировка."
    ),
    responses={401: {"model": ErrorResponse, "description": "Требуется авторизация"}},
)
def list_bookings(
    filters: Annotated[BookingFilter, Query()],
    service: BookingServiceDep,
    user: CurrentUser,
) -> BookingPage:
    return service.list_bookings(filters, user)


@router.get(
    "/{booking_id}",
    response_model=BookingOut,
    summary="Получить бронирование",
    responses={
        403: {"model": ErrorResponse, "description": "Бронирование принадлежит другому гостю"},
        404: {"model": ErrorResponse, "description": "Бронирование не найдено"},
    },
)
def get_booking(booking_id: int, service: BookingServiceDep, user: CurrentUser) -> BookingOut:
    return service.get_booking(booking_id, user)


@router.post(
    "/{booking_id}/cancel",
    response_model=BookingOut,
    summary="Отменить бронирование",
    description="Отмена доступна гостю-владельцу и администратору. Оплаченное бронирование требует возврата средств.",
    responses={
        403: {"model": ErrorResponse, "description": "Бронирование принадлежит другому гостю"},
        404: {"model": ErrorResponse, "description": "Бронирование не найдено"},
        409: {"model": ErrorResponse, "description": "Недопустимое изменение статуса"},
    },
)
def cancel_booking(
    booking_id: int,
    service: BookingServiceDep,
    user: CurrentUser,
    payload: BookingCancelRequest | None = None,
) -> BookingOut:
    reason = payload.reason if payload else None
    return service.cancel_booking(booking_id, user, reason=reason)


@router.post(
    "/{booking_id}/complete",
    response_model=BookingOut,
    summary="Завершить проживание (администратор)",
    description="Доступно только для полностью оплаченного бронирования.",
    responses={
        403: {"model": ErrorResponse, "description": "Недостаточно прав"},
        404: {"model": ErrorResponse, "description": "Бронирование не найдено"},
        409: {"model": ErrorResponse, "description": "Бронирование не оплачено или закрыто"},
    },
)
def complete_booking(booking_id: int, service: BookingServiceDep, _: AdminUser) -> BookingOut:
    return service.complete_booking(booking_id)
