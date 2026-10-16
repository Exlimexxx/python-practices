"""Маршруты номерного фонда."""
from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Body, Query, Response, status

from app.api.deps import AdminUser, RoomServiceDep
from app.models.enums import RoomStatus, RoomType
from app.schemas.common import ErrorResponse
from app.schemas.room import RoomCreate, RoomFilter, RoomOut, RoomPage, RoomUpdate

router = APIRouter(prefix="/rooms", tags=["rooms"])


@router.get(
    "",
    response_model=RoomPage,
    summary="Каталог номеров",
    description=(
        "Поддерживает фильтрацию по типу, статусу, цене, этажу и вместимости, "
        "а также сортировку и постраничную выдачу."
    ),
    responses={422: {"model": ErrorResponse, "description": "Некорректные параметры фильтра"}},
)
def list_rooms(filters: Annotated[RoomFilter, Query()], service: RoomServiceDep) -> RoomPage:
    return service.search_rooms(filters)


@router.get(
    "/available",
    response_model=list[RoomOut],
    summary="Свободные номера на период",
    description="Исключает номера с пересекающимися подтверждёнными бронированиями.",
    responses={422: {"model": ErrorResponse, "description": "Некорректный период"}},
)
def available_rooms(
    service: RoomServiceDep,
    check_in: date,
    check_out: date,
    min_capacity: Annotated[int | None, Query(ge=1, le=10)] = None,
    room_type: RoomType | None = None,
) -> list[RoomOut]:
    return service.available_rooms(
        check_in, check_out, min_capacity=min_capacity, room_type=room_type
    )


@router.post(
    "",
    response_model=RoomOut,
    status_code=status.HTTP_201_CREATED,
    summary="Добавить номер",
    responses={
        403: {"model": ErrorResponse, "description": "Недостаточно прав"},
        409: {"model": ErrorResponse, "description": "Номер с таким значением уже есть"},
    },
)
def create_room(payload: RoomCreate, service: RoomServiceDep, _: AdminUser) -> RoomOut:
    return service.create_room(payload)


@router.get(
    "/{room_id}",
    response_model=RoomOut,
    summary="Получить номер по идентификатору",
    responses={404: {"model": ErrorResponse, "description": "Номер не найден"}},
)
def get_room(room_id: int, service: RoomServiceDep) -> RoomOut:
    return service.get_room(room_id)


@router.patch(
    "/{room_id}",
    response_model=RoomOut,
    summary="Изменить номер",
    responses={
        403: {"model": ErrorResponse, "description": "Недостаточно прав"},
        404: {"model": ErrorResponse, "description": "Номер не найден"},
        422: {"model": ErrorResponse, "description": "Пустой запрос изменений"},
    },
)
def update_room(
    room_id: int, payload: RoomUpdate, service: RoomServiceDep, _: AdminUser
) -> RoomOut:
    return service.update_room(room_id, payload)


@router.put(
    "/{room_id}/status",
    response_model=RoomOut,
    summary="Изменить статус номера",
    description="Например, перевести номер в состояние maintenance или available.",
    responses={404: {"model": ErrorResponse, "description": "Номер не найден"}},
)
def change_room_status(
    room_id: int,
    service: RoomServiceDep,
    _: AdminUser,
    room_status: Annotated[RoomStatus, Body(embed=True, alias="status")],
) -> RoomOut:
    return service.change_status(room_id, room_status)


@router.delete(
    "/{room_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить номер",
    description="Удаление запрещено, если по номеру есть активные бронирования.",
    responses={
        404: {"model": ErrorResponse, "description": "Номер не найден"},
        409: {"model": ErrorResponse, "description": "По номеру есть бронирования"},
    },
)
def delete_room(room_id: int, service: RoomServiceDep, _: AdminUser) -> Response:
    service.delete_room(room_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
