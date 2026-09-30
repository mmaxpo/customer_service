from __future__ import annotations

import importlib
import uuid
import warnings
from datetime import datetime, timedelta, timezone

import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.models import User as UserORM
from app.models.schemas import UserCreate, UserInDB

SECRET_KEY: str = settings.SECRET_KEY
ALGORITHM = "HS256"


class EmailAlreadyRegisteredError(Exception):
    """The requested email already belongs to an account."""


class InvalidIdentityTokenError(Exception):
    """The supplied identity token cannot be trusted."""


# passlib currently emits a Python crypt deprecation warning while
# loading compatibility handlers. Keep that implementation detail
# outside the HTTP layer.
warnings.filterwarnings(
    "ignore",
    "'crypt' is deprecated",
    DeprecationWarning,
    module="passlib",
)


def _make_pwd_context():
    """Argon2 for new hashes; bcrypt retained for legacy verification."""

    crypt_context = importlib.import_module("passlib.context").CryptContext

    return crypt_context(
        schemes=[
            "argon2",
            "bcrypt_sha256",
            "bcrypt",
        ],
        deprecated="auto",
    )


pwd_context = _make_pwd_context()


class LegalAcceptanceRequiredError(ValueError):
    """Raised when required registration legal acceptance is missing."""


class PasswordPolicyError(ValueError):
    """Raised when a password does not satisfy the v1 account policy."""


def normalize_email(email: str) -> str:
    """Return the canonical identity form used for storage and lookup."""
    return email.strip().casefold()


def validate_password_policy(password: str) -> str:
    """Validate the shared v1 account password policy."""
    if len(password) < 12:
        raise PasswordPolicyError("Password must be at least 12 characters long")
    if not any(char.islower() for char in password):
        raise PasswordPolicyError("Password must contain a lowercase letter")
    if not any(char.isupper() for char in password):
        raise PasswordPolicyError("Password must contain an uppercase letter")
    if not any(char.isdigit() for char in password):
        raise PasswordPolicyError("Password must contain a number")
    if not any(not char.isalnum() for char in password):
        raise PasswordPolicyError("Password must contain a symbol")
    return password


def hash_password(
    password: str,
) -> str:
    return pwd_context.hash(password)


def verify_password(
    plain: str,
    hashed: str,
) -> bool:
    return pwd_context.verify(
        plain,
        hashed,
    )


def _timestamp(
    value: datetime,
) -> int:
    return int(value.replace(tzinfo=timezone.utc).timestamp())


def create_access_token(
    data: dict,
    *,
    expires_delta: timedelta | None = None,
    token_type: str = "access",
) -> str:
    now = datetime.now(timezone.utc)

    expire = now + (expires_delta or timedelta(minutes=15))

    payload = data | {
        "typ": token_type,
        "jti": str(uuid.uuid4()),
        "iat": _timestamp(now),
        "exp": _timestamp(expire),
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def decode_identity_claims(
    token: str,
    *,
    expected_type: str | None = None,
) -> dict:
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )
    except jwt.PyJWTError as exc:
        raise InvalidIdentityTokenError("Invalid identity token") from exc

    token_type = payload.get("typ")
    if expected_type is not None and token_type != expected_type:
        raise InvalidIdentityTokenError(
            f"Expected {expected_type} token",
        )

    if not payload.get("uid") and not payload.get("sub"):
        raise InvalidIdentityTokenError("Identity token has no subject")

    return payload


def decode_identity_token(
    token: str,
) -> tuple[str | None, str | None]:
    payload = decode_identity_claims(token)

    uid = payload.get("uid")
    email = payload.get("sub")

    if not uid and not email:
        raise InvalidIdentityTokenError("Identity token has no subject")

    return (
        str(uid) if uid else None,
        str(email) if email else None,
    )


async def get_user_by_email(
    email: str,
    session: AsyncSession,
) -> UserInDB | None:
    email = normalize_email(email)
    result = await session.execute(
        select(UserORM).where(UserORM.normalized_email == email)
    )

    row = result.scalar_one_or_none()

    if row is None:
        return None

    return UserInDB.model_validate(
        row,
        from_attributes=True,
    )


async def get_user_by_id(
    user_id: str,
    session: AsyncSession,
) -> UserInDB | None:
    result = await session.execute(select(UserORM).where(UserORM.id == user_id))

    row = result.scalar_one_or_none()

    if row is None:
        return None

    return UserInDB.model_validate(
        row,
        from_attributes=True,
    )


async def authenticate_user(
    email: str,
    password: str,
    session: AsyncSession,
) -> UserInDB | None:
    user = await get_user_by_email(
        email,
        session,
    )

    if (
        user is None
        or not user.is_active
        or not verify_password(
            password,
            user.hashed_password,
        )
    ):
        return None

    return user


async def create_user(
    data: UserCreate,
    session: AsyncSession,
) -> UserInDB:
    normalized_email = normalize_email(str(data.email))
    validate_password_policy(data.password)

    if data.terms_accepted is not True:
        raise LegalAcceptanceRequiredError("Terms of Service acceptance is required")
    if data.privacy_accepted is not True:
        raise LegalAcceptanceRequiredError("Privacy Policy acceptance is required")

    terms_version = data.terms_version.strip()
    privacy_version = data.privacy_version.strip()

    if not terms_version:
        raise LegalAcceptanceRequiredError("Terms of Service version is required")
    if len(terms_version) > 64:
        raise LegalAcceptanceRequiredError("Terms of Service version is too long")
    if not privacy_version:
        raise LegalAcceptanceRequiredError("Privacy Policy version is required")
    if len(privacy_version) > 64:
        raise LegalAcceptanceRequiredError("Privacy Policy version is too long")

    accepted_at = datetime.now(timezone.utc)
    existing = await get_user_by_email(
        data.email,
        session,
    )

    if existing is not None:
        raise EmailAlreadyRegisteredError(data.email)

    row = UserORM(
        email=normalized_email,
        normalized_email=normalized_email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        terms_accepted_at=accepted_at,
        terms_version=terms_version,
        privacy_accepted_at=accepted_at,
        privacy_version=privacy_version,
    )

    session.add(row)
    await session.flush()

    from app.tenancy.service import provision_personal_workspace

    await provision_personal_workspace(
        session,
        user_id=row.id,
        email=row.email,
        full_name=row.full_name,
    )
    await session.commit()

    return UserInDB.model_validate(
        row,
        from_attributes=True,
    )


__all__ = [
    "EmailAlreadyRegisteredError",
    "InvalidIdentityTokenError",
    "authenticate_user",
    "create_access_token",
    "create_user",
    "decode_identity_claims",
    "decode_identity_token",
    "get_user_by_email",
    "get_user_by_id",
    "hash_password",
    "verify_password",
]
