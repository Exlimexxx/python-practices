"""Тесты хеширования паролей и JWT-токенов."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.config import Settings
from app.exceptions import AuthenticationError
from app.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


@pytest.fixture()
def settings() -> Settings:
    return Settings(jwt_secret="unit-secret-unit-secret-unit-secret", access_token_ttl_minutes=15)


def test_hash_password_is_salted_and_verifiable():
    first = hash_password("secret-pass-123")
    second = hash_password("secret-pass-123")
    assert first != second
    assert verify_password("secret-pass-123", first)
    assert verify_password("secret-pass-123", second)


def test_verify_password_rejects_wrong_value():
    stored = hash_password("secret-pass-123")
    assert verify_password("another-pass-123", stored) is False


def test_hash_password_rejects_short_password():
    with pytest.raises(ValueError):
        hash_password("short")


@pytest.mark.parametrize(
    "broken_hash",
    ["", "not-a-hash", "md5$1$AA$BB", "pbkdf2_sha256$not-a-number$AA$BB"],
)
def test_verify_password_handles_broken_hash(broken_hash):
    assert verify_password("secret-pass-123", broken_hash) is False


def test_access_token_round_trip(settings: Settings):
    token, expires_in = create_access_token(7, role="admin", settings=settings)
    payload = decode_access_token(token, settings=settings)
    assert payload["sub"] == "7"
    assert payload["role"] == "admin"
    assert expires_in == 15 * 60


def test_expired_token_is_rejected(settings: Settings):
    issued_at = datetime.now(timezone.utc) - timedelta(minutes=settings.access_token_ttl_minutes + 5)
    token, _ = create_access_token(1, role="user", settings=settings, now=issued_at)
    with pytest.raises(AuthenticationError):
        decode_access_token(token, settings=settings)


def test_token_signed_with_other_secret_is_rejected(settings: Settings):
    other = Settings(jwt_secret="other-secret-other-secret-other", access_token_ttl_minutes=15)
    token, _ = create_access_token(1, role="user", settings=other)
    with pytest.raises(AuthenticationError):
        decode_access_token(token, settings=settings)
