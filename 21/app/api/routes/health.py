"""Проверка работоспособности сервиса."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.common import ErrorResponse

router = APIRouter(tags=["service"])


@router.get(
    "/health",
    summary="Проверка работоспособности",
    description="Возвращает состояние сервиса и подтверждает доступность базы данных.",
    responses={503: {"model": ErrorResponse, "description": "База данных недоступна"}},
)
def health(request: Request, session: Annotated[Session, Depends(get_db)]) -> dict:
    session.execute(select(1))
    settings = request.app.state.settings
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
    }
