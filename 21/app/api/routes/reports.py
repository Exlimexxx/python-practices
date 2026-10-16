"""Маршруты аналитики."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import AdminUser, ReportServiceDep
from app.schemas.common import ErrorResponse
from app.schemas.report import ReportSummary

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get(
    "/summary",
    response_model=ReportSummary,
    summary="Сводная статистика гостиницы (администратор)",
    description=(
        "Объединяет данные о пользователях, номерах, бронированиях и платежах: "
        "выручка, возвраты, средняя стоимость проживания и популярный тип номера."
    ),
    responses={403: {"model": ErrorResponse, "description": "Недостаточно прав"}},
)
def summary(service: ReportServiceDep, _: AdminUser) -> ReportSummary:
    return service.summary()
