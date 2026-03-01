from __future__ import annotations

import time

import pytest

from src.core.auth.jwt import TokenError, create_access_token, decode_access_token

SECRET = "test-secret-key-for-jwt"


def test_create_and_decode():
    token = create_access_token(
        user_id="u1",
        tenant_id="t1",
        email="test@example.com",
        secret_key=SECRET,
    )
    payload = decode_access_token(token, secret_key=SECRET)

    assert payload["sub"] == "u1"
    assert payload["tenant_id"] == "t1"
    assert payload["email"] == "test@example.com"
    assert payload["type"] == "access"


def test_expired_token():
    token = create_access_token(
        user_id="u1",
        tenant_id="t1",
        email="test@example.com",
        secret_key=SECRET,
        expire_minutes=-1,  # Already expired
    )
    with pytest.raises(TokenError, match="expired"):
        decode_access_token(token, secret_key=SECRET)


def test_bad_signature():
    token = create_access_token(
        user_id="u1",
        tenant_id="t1",
        email="test@example.com",
        secret_key=SECRET,
    )
    with pytest.raises(TokenError, match="Invalid token"):
        decode_access_token(token, secret_key="wrong-key")


def test_tampered_token():
    token = create_access_token(
        user_id="u1",
        tenant_id="t1",
        email="test@example.com",
        secret_key=SECRET,
    )
    # Tamper with the payload
    parts = token.split(".")
    parts[1] = parts[1] + "x"
    tampered = ".".join(parts)

    with pytest.raises(TokenError):
        decode_access_token(tampered, secret_key=SECRET)


def test_custom_algorithm():
    token = create_access_token(
        user_id="u1",
        tenant_id="t1",
        email="test@example.com",
        secret_key=SECRET,
        algorithm="HS384",
    )
    payload = decode_access_token(token, secret_key=SECRET, algorithm="HS384")
    assert payload["sub"] == "u1"


def test_custom_expiry():
    token = create_access_token(
        user_id="u1",
        tenant_id="t1",
        email="test@example.com",
        secret_key=SECRET,
        expire_minutes=60,
    )
    payload = decode_access_token(token, secret_key=SECRET)
    assert payload["exp"] > time.time()
