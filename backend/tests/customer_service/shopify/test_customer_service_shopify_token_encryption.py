from app.core.security.secrets import decrypt_secret, encrypt_secret


def test_shopify_secret_encryption_dev_fallback_round_trip(monkeypatch):
    monkeypatch.delenv("TAJERAN_FIELD_ENCRYPTION_KEY", raising=False)
    monkeypatch.delenv("SHOPIFY_TOKEN_ENCRYPTION_KEY", raising=False)

    encrypted = encrypt_secret("shpat_secret")

    assert encrypted == "plain:shpat_secret"
    assert decrypt_secret(encrypted) == "shpat_secret"


def test_shopify_secret_encryption_fernet_round_trip(monkeypatch):
    from app.core.security.secrets import generate_secret_key

    monkeypatch.setenv("TAJERAN_FIELD_ENCRYPTION_KEY", generate_secret_key())

    encrypted = encrypt_secret("shpat_secret")

    assert encrypted is not None
    assert encrypted.startswith("fernet:")
    assert "shpat_secret" not in encrypted
    assert decrypt_secret(encrypted) == "shpat_secret"


def test_legacy_plain_token_still_decrypts():
    assert decrypt_secret("legacy-token") == "legacy-token"
