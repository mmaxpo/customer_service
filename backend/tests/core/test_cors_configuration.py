import pytest

from app.core.cors import (
    cors_allowed_origins,
)


def test_dev_default(
    monkeypatch,
):
    monkeypatch.setenv(
        "APP_ENV",
        "development",
    )
    monkeypatch.delenv(
        "CORS_ALLOWED_ORIGINS",
        raising=False,
    )

    assert cors_allowed_origins() == ["http://localhost:3000"]


def test_explicit_origins(
    monkeypatch,
):
    monkeypatch.setenv(
        "APP_ENV",
        "development",
    )
    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS",
        ("http://localhost:3000,http://127.0.0.1:3001"),
    )

    assert cors_allowed_origins() == [
        "http://localhost:3000",
        "http://127.0.0.1:3001",
    ]


def test_wildcard_rejected(
    monkeypatch,
):
    monkeypatch.setenv(
        "APP_ENV",
        "development",
    )
    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS",
        "*",
    )

    with pytest.raises(RuntimeError):
        cors_allowed_origins()


def test_prod_requires_explicit(
    monkeypatch,
):
    monkeypatch.setenv(
        "APP_ENV",
        "production",
    )
    monkeypatch.delenv(
        "CORS_ALLOWED_ORIGINS",
        raising=False,
    )

    with pytest.raises(RuntimeError):
        cors_allowed_origins()


@pytest.mark.parametrize(
    "origin",
    [
        "http://app.example.com",
        "https://localhost:3000",
        "https://127.0.0.1:3000",
    ],
)
def test_prod_rejects_unsafe(
    monkeypatch,
    origin,
):
    monkeypatch.setenv(
        "APP_ENV",
        "production",
    )
    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS",
        origin,
    )

    with pytest.raises(RuntimeError):
        cors_allowed_origins()


def test_prod_accepts_https(
    monkeypatch,
):
    monkeypatch.setenv(
        "APP_ENV",
        "production",
    )
    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS",
        "https://app.example.com",
    )

    assert cors_allowed_origins() == ["https://app.example.com"]
