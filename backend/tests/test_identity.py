import pytest

from app.identity import (
    InvalidIdentityTokenError,
    create_access_token,
    decode_identity_token,
    hash_password,
    verify_password,
)


def test_password_hash_round_trip():
    encoded = hash_password("correct horse battery staple")

    assert encoded != ("correct horse battery staple")

    assert verify_password(
        "correct horse battery staple",
        encoded,
    )

    assert not verify_password(
        "wrong-password",
        encoded,
    )


def test_identity_token_round_trip():
    token = create_access_token(
        {
            "uid": "user-123",
            "sub": "user@example.com",
        }
    )

    uid, email = decode_identity_token(token)

    assert uid == "user-123"
    assert email == "user@example.com"


def test_identity_token_requires_subject():
    token = create_access_token(
        {
            "purpose": "test",
        }
    )

    with pytest.raises(InvalidIdentityTokenError):
        decode_identity_token(token)


def test_invalid_identity_token_is_normalized():
    with pytest.raises(InvalidIdentityTokenError):
        decode_identity_token("not-a-jwt")
