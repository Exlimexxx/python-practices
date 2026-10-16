"""Роутер /movies — только HTTP-слой, без SQL (п. 15, 22, 32 методички).

Порядок объявления важен: статические пути (/by-genre, /search, /stats)
объявлены раньше динамического /{movie_id}, иначе он их перехватит.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy.orm import Session

from ..cache import get_cache
from ..database import get_db
from ..repositories.movie import MovieRepository
from ..schemas.movie import (
    ErrorResponse,
    MovieCreate,
    MovieListResponse,
    MovieResponse,
    MovieStats,
    MovieUpdate,
)
from ..services.movie import MovieService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/movies", tags=["movies"])

ERROR_RESPONSES = {
    400: {"model": ErrorResponse, "description": "Некорректные параметры запроса"},
    404: {"model": ErrorResponse, "description": "Фильм не найден"},
    422: {"model": ErrorResponse, "description": "Ошибка валидации Pydantic"},
    500: {"model": ErrorResponse, "description": "Внутренняя ошибка сервера"},
}


def get_movie_service(db: Session = Depends(get_db)) -> MovieService:
    """Dependency Injection: собирает Service из Repository и кэша."""
    return MovieService(MovieRepository(db), get_cache())


# ------------------------------------------------------- специальные выборки
@router.get(
    "/by-genre",
    response_model=MovieListResponse,
    summary="Фильмы по жанру",
    description="Возвращает фильмы указанного жанра. Регистронезависимый поиск, сортировка по рейтингу.",
    responses=ERROR_RESPONSES,
)
def get_movies_by_genre(
    genre: str = Query(..., min_length=1, max_length=100, description="Название жанра"),
    limit: int = Query(20, ge=1, le=100, description="Размер страницы"),
    offset: int = Query(0, ge=0, description="Смещение"),
    service: MovieService = Depends(get_movie_service),
) -> MovieListResponse:
    return service.movies_by_genre(genre, limit=limit, offset=offset)


@router.get(
    "/search",
    response_model=MovieListResponse,
    summary="Поиск фильмов",
    description="Поиск по названию, режиссёру и описанию (регистронезависимо).",
    responses=ERROR_RESPONSES,
)
def search_movies(
    q: str = Query(..., min_length=1, max_length=200, description="Поисковый запрос"),
    limit: int = Query(20, ge=1, le=100, description="Размер страницы"),
    offset: int = Query(0, ge=0, description="Смещение"),
    service: MovieService = Depends(get_movie_service),
) -> MovieListResponse:
    return service.search_movies(q, limit=limit, offset=offset)


@router.get(
    "/stats",
    response_model=MovieStats,
    summary="Статистика фильмов",
    description="Количество фильмов, средний/мин/макс рейтинг, распределение по жанрам.",
    responses={500: ERROR_RESPONSES[500]},
)
async def get_movies_stats(
    service: MovieService = Depends(get_movie_service),
) -> MovieStats:
    # async def: обработчик не блокирует event loop при ожидании I/O (п. 35, 36).
    return await service.get_stats()


# --------------------------------------------------------------------- CRUD
@router.get(
    "",
    response_model=MovieListResponse,
    summary="Список фильмов",
    description="Фильтрация (genre, min_rating, year), сортировка (sort/order) и пагинация (limit/offset).",
    responses=ERROR_RESPONSES,
)
def get_movies(
    genre: str | None = Query(None, max_length=100, description="Фильтр по жанру"),
    min_rating: float | None = Query(None, ge=0, le=10, description="Минимальный рейтинг"),
    year: int | None = Query(None, ge=1888, le=2100, description="Год выпуска"),
    sort: str = Query("id", description="Поле сортировки"),
    order: str = Query("asc", description="Направление сортировки: asc или desc"),
    limit: int = Query(20, ge=1, le=100, description="Размер страницы"),
    offset: int = Query(0, ge=0, description="Смещение"),
    service: MovieService = Depends(get_movie_service),
) -> MovieListResponse:
    return service.list_movies(
        genre=genre,
        min_rating=min_rating,
        year=year,
        sort=sort,
        order=order,
        limit=limit,
        offset=offset,
    )


@router.post(
    "",
    response_model=MovieResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать фильм",
    description="Принимает JSON, валидирует Pydantic-схемой и сохраняет фильм. Возвращает 201.",
    responses={422: ERROR_RESPONSES[422], 500: ERROR_RESPONSES[500]},
)
async def create_movie(
    payload: MovieCreate,
    service: MovieService = Depends(get_movie_service),
) -> MovieResponse:
    return await service.create_movie(payload)


@router.get(
    "/{movie_id}",
    response_model=MovieResponse,
    summary="Получить фильм по id",
    description="Кэшируемый endpoint: сначала проверяется Redis, затем БД (cache-aside).",
    responses=ERROR_RESPONSES,
)
async def get_movie(
    movie_id: int = Path(..., ge=1, description="Идентификатор фильма"),
    service: MovieService = Depends(get_movie_service),
) -> MovieResponse:
    return await service.get_movie(movie_id)


@router.put(
    "/{movie_id}",
    response_model=MovieResponse,
    summary="Полностью обновить фильм",
    description="PUT заменяет все поля фильма переданным объектом.",
    responses=ERROR_RESPONSES,
)
async def replace_movie(
    payload: MovieCreate,
    movie_id: int = Path(..., ge=1, description="Идентификатор фильма"),
    service: MovieService = Depends(get_movie_service),
) -> MovieResponse:
    return await service.replace_movie(movie_id, payload)


@router.patch(
    "/{movie_id}",
    response_model=MovieResponse,
    summary="Частично обновить фильм",
    description="PATCH изменяет только те поля, которые присутствуют в теле запроса.",
    responses=ERROR_RESPONSES,
)
async def patch_movie(
    payload: MovieUpdate,
    movie_id: int = Path(..., ge=1, description="Идентификатор фильма"),
    service: MovieService = Depends(get_movie_service),
) -> MovieResponse:
    return await service.patch_movie(movie_id, payload)


@router.delete(
    "/{movie_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить фильм",
    description="Удаляет фильм и сбрасывает его кэш. Возвращает 204 без тела.",
    responses={204: {"description": "Удалено"}, **ERROR_RESPONSES},
)
async def delete_movie(
    movie_id: int = Path(..., ge=1, description="Идентификатор фильма"),
    service: MovieService = Depends(get_movie_service),
) -> Response:
    await service.delete_movie(movie_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
