"""Маршруты платежей и возвратов."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import AdminUser, CurrentUser, PaymentServiceDep
from app.schemas.common import ErrorResponse, Page
from app.schemas.payment import PaymentCreate, PaymentOut

router = APIRouter(tags=["payments"])


@router.post(
    "/payments",
    response_model=PaymentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Оплатить бронирование",
    description="Сумма платежа не может превышать остаток к оплате по бронированию.",
    responses={
        401: {"model": ErrorResponse, "description": "Требуется авторизация"},
        403: {"model": ErrorResponse, "description": "Бронирование принадлежит другому гостю"},
        404: {"model": ErrorResponse, "description": "Бронирование не найдено"},
        409: {"model": ErrorResponse, "description": "Превышение суммы или статус бронирования"},
    },
)
def pay(payload: PaymentCreate, service: PaymentServiceDep, user: CurrentUser) -> PaymentOut:
    return service.pay(payload, user)


@router.get(
    "/bookings/{booking_id}/payments",
    response_model=list[PaymentOut],
    summary="Платежи по бронированию",
    responses={403: {"model": ErrorResponse, "description": "Недостаточно прав"}},
)
def booking_payments(
    booking_id: int, service: PaymentServiceDep, user: CurrentUser
) -> list[PaymentOut]:
    return service.list_for_booking(booking_id, user)


@router.get(
    "/payments",
    response_model=Page[PaymentOut],
    summary="Все платежи (администратор)",
    responses={403: {"model": ErrorResponse, "description": "Недостаточно прав"}},
)
def list_payments(
    service: PaymentServiceDep,
    _: AdminUser,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[PaymentOut]:
    items, total = service.list_payments(limit=limit, offset=offset)
    return Page[PaymentOut](total=total, limit=limit, offset=offset, items=items)


@router.post(
    "/payments/{payment_id}/refund",
    response_model=PaymentOut,
    summary="Вернуть средства (администратор)",
    responses={
        403: {"model": ErrorResponse, "description": "Недостаточно прав"},
        404: {"model": ErrorResponse, "description": "Платёж не найден"},
        409: {"model": ErrorResponse, "description": "Платёж уже возвращён"},
    },
)
def refund_payment(payment_id: int, service: PaymentServiceDep, _: AdminUser) -> PaymentOut:
    return service.refund(payment_id)
