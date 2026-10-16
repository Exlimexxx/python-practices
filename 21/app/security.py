"""Хеширование паролей и работа с JWT-токенами."""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt

from app.config import Settings
from app.exceptions import AuthenticationError

PBKDF2_ALGORITHM = "pbkdf2_sha256"
PBKDF2_ITERATIONS = 120_000
SALT_SIZE = 16
MIN_PASSWORD_LENGTH = 8


def hash_password(
    password: str,
    *,
    iterations: int = PBKDF2_ITERATIONS,
    salt: bytes | None = None,
) -> str:
    """Вернуть строку вида ``pbkdf2_sha256$итерации$соль$хеш``."""
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError("Пароль должен содержать не менее 8 символов")
    salt = salt or os.urandom(SALT_SIZE)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    salt_b64 = base64.b64encode(salt).decode("ascii")
    digest_b64 = base64.b64encode(digest).decode("ascii")
    return f"{PBKDF2_ALGORITHM}${iterations}${salt_b64}${digest_b64}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Сравнить пароль с сохранённым хешем в постоянном времени."""
    try:
        algorithm, iterations, salt_b64, digest_b64 = stored_hash.split("$")
        if algorithm != PBKDF2_ALGORITHM:
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            base64.b64decode(salt_b64),
            int(iterations),
        )
        expected = base64.b64decode(digest_b64)
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest, expected)


def create_access_token(
    user_id: int,
    *,
    role: str,
    settings: Settings,
    now: datetime | None = None,
) -> tuple[str, int]:
    """Выпустить JWT и вернуть его вместе со сроком жизни в секундах."""
    issued_at = now or datetime.now(timezone.utc)
    lifetime = timedelta(minutes=settings.access_token_ttl_minutes)
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": int(issued_at.timestamp()),
        "exp": int((issued_at + lifetime).timestamp()),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, int(lifetime.total_seconds())


def decode_access_token(token: str, *, settings: Settings) -> dict:
    """Проверить подпись и срок действия токена."""
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError("Срок действия токена истёк") from exc
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Некорректный токен доступа") from exc
