from __future__ import annotations

from src.core.auth.password import hash_password, verify_password


def test_hash_and_verify():
    hashed = hash_password("MyPassword1")
    assert verify_password("MyPassword1", hashed)


def test_wrong_password_fails():
    hashed = hash_password("MyPassword1")
    assert not verify_password("WrongPassword1", hashed)


def test_hash_is_unique():
    h1 = hash_password("MyPassword1")
    h2 = hash_password("MyPassword1")
    # bcrypt salts differ each time
    assert h1 != h2


def test_hash_is_string():
    result = hash_password("SomePass1")
    assert isinstance(result, str)
    assert result.startswith("$2")
