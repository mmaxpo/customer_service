import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken

from app.core.environment import is_production_environment

_PREFIX = "enc:v1:"


def _key() -> bytes:
    raw = os.getenv("SHOPIFY_TOKEN_ENCRYPTION_KEY") or os.getenv(
        "TAJERAN_ENCRYPTION_KEY"
    )
    if raw:
        return raw.encode()

    if is_production_environment():
        raise RuntimeError("SHOPIFY_TOKEN_ENCRYPTION_KEY is required in production")

    seed = (
        os.getenv("SECRET_KEY")
        or os.getenv("JWT_SECRET_KEY")
        or "tajeran-dev-only-encryption-key"
    )
    return base64.urlsafe_b64encode(hashlib.sha256(seed.encode()).digest())


def encrypt_secret(value: str | None) -> str | None:
    if value is None:
        return None
    if value.startswith(_PREFIX):
        return value
    return _PREFIX + Fernet(_key()).encrypt(value.encode()).decode()


def decrypt_secret(value: str | None) -> str | None:
    if value is None:
        return None
    if not value.startswith(_PREFIX):
        return value  # legacy plaintext compatibility
    token = value.removeprefix(_PREFIX)
    try:
        return Fernet(_key()).decrypt(token.encode()).decode()
    except InvalidToken as exc:
        raise RuntimeError("Unable to decrypt stored secret") from exc
