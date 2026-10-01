import os

from cryptography.fernet import Fernet, InvalidToken


KEY_ENV_NAMES = (
    "TAJERAN_FIELD_ENCRYPTION_KEY",
    "SHOPIFY_TOKEN_ENCRYPTION_KEY",
)


def generate_secret_key() -> str:
    return Fernet.generate_key().decode("utf-8")


def _key() -> bytes | None:
    for name in KEY_ENV_NAMES:
        value = os.getenv(name)
        if value:
            return value.encode("utf-8")
    return None


def _fernet() -> Fernet | None:
    key = _key()
    if not key:
        return None
    try:
        return Fernet(key)
    except Exception as exc:
        raise ValueError("Invalid field encryption key") from exc


def encrypt_secret(value: str | None) -> str | None:
    if value is None:
        return None

    fernet = _fernet()
    if fernet is None:
        # Dev/test fallback only. Production must set TAJERAN_FIELD_ENCRYPTION_KEY.
        return "plain:" + value

    encrypted = fernet.encrypt(value.encode("utf-8")).decode("utf-8")
    return "fernet:" + encrypted


def decrypt_secret(value: str | None) -> str | None:
    if value is None:
        return None

    if value.startswith("plain:"):
        return value.removeprefix("plain:")

    if value.startswith("fernet:"):
        fernet = _fernet()
        if fernet is None:
            raise ValueError("Missing field encryption key")
        token = value.removeprefix("fernet:").encode("utf-8")
        try:
            return fernet.decrypt(token).decode("utf-8")
        except InvalidToken as exc:
            raise ValueError("Invalid encrypted secret") from exc

    # Backward compatibility for old tokens already saved before encryption.
    return value
