from app.core.security.secrets import (
    decrypt_secret,
    encrypt_secret,
    generate_secret_key,
)


def test_webhook_secret_uses_shared_field_encryption(monkeypatch):
    monkeypatch.setenv("TAJERAN_FIELD_ENCRYPTION_KEY", generate_secret_key())

    encrypted = encrypt_secret("super-secret")

    assert encrypted is not None
    assert encrypted.startswith("fernet:")
    assert "super-secret" not in encrypted
    assert decrypt_secret(encrypted) == "super-secret"
