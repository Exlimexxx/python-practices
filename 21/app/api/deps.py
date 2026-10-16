"""Зависимости FastAPI: сессия БД, текущий пользователь, сервисы."""
from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import Settings
from app.exceptions import AuthenticationError, PermissionDeniedError
from app.models import User, UserRole
from app.repositories.booking_repository import BookingRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.room_repository import RoomRepository
from app.repositories.user_repository import UserRepository
from app.security import decode_access_token
from app.services.booking_service import BookingService
from app.services.payment_service import PaymentService
from app.services.report_service import ReportService
from app.services.room_service import RoomService
from app.services.user_service import UserService

bearer_scheme = HTTPBearer(auto_error=False)


def get_settings_from_app(request: Request) -> Settings:
    return request.app.state.settings


def get_db(request: Request) -> Iterator[Session]:
    """Сессия БД на время обработки одного HTTP-запроса."""
    session = request.app.state.session_factory()
    try:
        yield session
    finally:
        session.close()


def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[Session, Depends(get_db)],
) -> User:
    if credentials is None or not credentials.credentials:
        raise AuthenticationError("Требуется заголовок Authorization с токеном доступа")
    settings: Settings = request.app.state.settings
    payload = decode_access_token(credentials.credentials, settings=settings)
    try:
        user_id = int(payload.get("sub", ""))
    except (TypeError, ValueError) as exc:
        raise AuthenticationError("Некорректный токен доступа") from exc
    user = UserRepository(session).get(user_id)
    if user is None:
        raise AuthenticationError("Пользователь из токена не найден")
    if not user.is_active:
        raise AuthenticationError("Учётная запись отключена")
    return user


def require_roles(*roles: UserRole):
    """Зависимость, разрешающая доступ только указанным ролям."""

    def dependency(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in roles:
            allowed = ", ".join(role.value for role in roles)
            raise PermissionDeniedError(
                f"Операция доступна ролям: {allowed}",
                details={"required_roles": [role.value for role in roles]},
            )
        return user

    return dependency


CurrentUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[User, Depends(require_roles(UserRole.ADMIN))]


def get_user_service(
    session: Annotated[Session, Depends(get_db)],
    request: Request,
) -> UserService:
    return UserService(session, UserRepository(session), request.app.state.settings)


def get_room_service(session: Annotated[Session, Depends(get_db)]) -> RoomService:
    return RoomService(session, RoomRepository(session), BookingRepository(session))


def get_booking_service(session: Annotated[Session, Depends(get_db)]) -> BookingService:
    return BookingService(
        session,
        BookingRepository(session),
        RoomRepository(session),
        PaymentRepository(session),
    )


def get_payment_service(session: Annotated[Session, Depends(get_db)]) -> PaymentService:
    return PaymentService(session, PaymentRepository(session), BookingRepository(session))


def get_report_service(session: Annotated[Session, Depends(get_db)]) -> ReportService:
    return ReportService(
        UserRepository(session),
        RoomRepository(session),
        BookingRepository(session),
        PaymentRepository(session),
    )


UserServiceDep = Annotated[UserService, Depends(get_user_service)]
RoomServiceDep = Annotated[RoomService, Depends(get_room_service)]
BookingServiceDep = Annotated[BookingService, Depends(get_booking_service)]
PaymentServiceDep = Annotated[PaymentService, Depends(get_payment_service)]
ReportServiceDep = Annotated[ReportService, Depends(get_report_service)]
