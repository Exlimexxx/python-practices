"""Проверки прав доступа, общие для сервисов."""
from __future__ import annotations

from app.exceptions import AuthenticationError, PermissionDeniedError
from app.models import User, UserRole


def require_authenticated_user(actor: User | None) -> User:
    if actor is None:
        raise AuthenticationError("Требуется авторизация")
    if not actor.is_active:
        raise PermissionDeniedError("Учётная запись отключена")
    return actor


def ensure_owner_or_admin(owner_id: int, actor: User | None, *, entity: str) -> User:
    """Разрешить действие владельцу объекта или администратору."""
    user = require_authenticated_user(actor)
    if user.role is UserRole.ADMIN or user.id == owner_id:
        return user
    raise PermissionDeniedError(
        f"Недостаточно прав для работы с объектом {entity}",
        details={"entity": entity, "owner_id": owner_id},
    )
