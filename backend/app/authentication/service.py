from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.authentication.models import AuthSession, IdentityActionToken
from app.core.config import settings
from app.identity import (
    InvalidIdentityTokenError,
    create_access_token,
    decode_identity_claims,
    hash_password,
    normalize_email,
    validate_password_policy,
    verify_password,
)
from app.models.models import User as UserORM
from app.models.schemas import UserInDB


class InvalidRefreshTokenError(Exception):
    """A refresh token is invalid, expired, revoked, or already used."""


class InvalidActionTokenError(Exception):
    """An account action token is invalid, expired, or already consumed."""


class InvalidCurrentPasswordError(Exception):
    """The supplied current password does not authenticate the user."""


class EmailAddressAlreadyInUseError(Exception):
    """The requested canonical email belongs to another account."""


class EmailAddressUnchangedError(Exception):
    """The requested email is already the account's current email."""


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _claims(user: UserInDB, row: AuthSession) -> dict[str, str | int]:
    return {
        "sub": user.email,
        "uid": str(user.id),
        "sid": str(row.id),
        "fid": str(row.family_id),
        "rot": row.rotation_counter,
    }


def _issue_pair(user: UserInDB, row: AuthSession) -> TokenPair:
    claims = _claims(user, row)
    return TokenPair(
        access_token=create_access_token(
            claims,
            expires_delta=timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
            ),
            token_type="access",
        ),
        refresh_token=create_access_token(
            claims,
            expires_delta=timedelta(
                minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES,
            ),
            token_type="refresh",
        ),
    )


async def create_session(
    session: AsyncSession,
    *,
    user: UserInDB,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> TokenPair:
    now = _now()
    row = AuthSession(
        id=uuid.uuid4(),
        user_id=user.id,
        family_id=uuid.uuid4(),
        refresh_token_hash="pending",
        rotation_counter=0,
        user_agent=(user_agent or "")[:512] or None,
        ip_address=(ip_address or "")[:64] or None,
        expires_at=now + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES),
    )
    pair = _issue_pair(user, row)
    row.refresh_token_hash = _token_hash(pair.refresh_token)
    session.add(row)
    await session.commit()
    return pair


async def rotate_refresh_token(
    session: AsyncSession,
    *,
    token: str,
    user: UserInDB,
) -> TokenPair:
    try:
        claims = decode_identity_claims(token, expected_type="refresh")
        session_id = uuid.UUID(str(claims["sid"]))
        family_id = uuid.UUID(str(claims["fid"]))
    except (InvalidIdentityTokenError, KeyError, TypeError, ValueError) as exc:
        raise InvalidRefreshTokenError from exc

    result = await session.execute(
        select(AuthSession).where(AuthSession.id == session_id).with_for_update(),
    )
    row = result.scalar_one_or_none()
    now = _now()

    if (
        row is None
        or row.user_id != user.id
        or row.family_id != family_id
        or row.revoked_at is not None
        or row.expires_at <= now
    ):
        raise InvalidRefreshTokenError

    if not hmac.compare_digest(row.refresh_token_hash, _token_hash(token)):
        await session.execute(
            update(AuthSession)
            .where(
                AuthSession.family_id == row.family_id,
                AuthSession.revoked_at.is_(None),
            )
            .values(
                revoked_at=now,
                revocation_reason="refresh_reuse",
            ),
        )
        await session.commit()
        raise InvalidRefreshTokenError

    row.rotation_counter += 1
    row.last_used_at = now
    pair = _issue_pair(user, row)
    row.refresh_token_hash = _token_hash(pair.refresh_token)
    await session.commit()
    return pair


async def is_session_active(
    session: AsyncSession,
    *,
    session_id: str,
    user_id: uuid.UUID,
) -> bool:
    try:
        parsed_id = uuid.UUID(session_id)
    except ValueError:
        return False

    result = await session.execute(
        select(AuthSession.id).where(
            AuthSession.id == parsed_id,
            AuthSession.user_id == user_id,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > _now(),
        ),
    )
    return result.scalar_one_or_none() is not None


async def list_active_sessions(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> list[AuthSession]:
    """Return the user's currently active server-side sessions."""
    result = await session.execute(
        select(AuthSession)
        .where(
            AuthSession.user_id == user_id,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > _now(),
        )
        .order_by(AuthSession.created_at.desc())
    )

    return list(result.scalars().all())


async def revoke_user_session(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    session_id: str,
    reason: str = "user_revoked",
) -> bool:
    """
    Revoke one session owned by the user.

    Ownership is part of the UPDATE predicate so another user's session
    can never be revoked through this operation.
    """
    try:
        parsed_id = uuid.UUID(session_id)
    except ValueError:
        return False

    result = await session.execute(
        update(AuthSession)
        .where(
            AuthSession.id == parsed_id,
            AuthSession.user_id == user_id,
            AuthSession.revoked_at.is_(None),
        )
        .values(
            revoked_at=_now(),
            revocation_reason=reason,
        )
    )

    await session.commit()
    return bool(result.rowcount)


async def revoke_other_user_sessions(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    current_session_id: str,
) -> int:
    """Revoke every active session except the caller's current session."""
    try:
        parsed_current_id = uuid.UUID(current_session_id)
    except ValueError as exc:
        raise InvalidIdentityTokenError("Invalid session identifier") from exc

    result = await session.execute(
        update(AuthSession)
        .where(
            AuthSession.user_id == user_id,
            AuthSession.id != parsed_current_id,
            AuthSession.revoked_at.is_(None),
        )
        .values(
            revoked_at=_now(),
            revocation_reason="logout_others",
        )
    )

    await session.commit()
    return int(result.rowcount or 0)


async def revoke_session_from_token(
    session: AsyncSession,
    *,
    token: str | None,
    reason: str = "logout",
) -> None:
    if not token:
        return
    try:
        claims = decode_identity_claims(token)
        session_id = uuid.UUID(str(claims["sid"]))
    except (InvalidIdentityTokenError, KeyError, TypeError, ValueError):
        return

    await session.execute(
        update(AuthSession)
        .where(
            AuthSession.id == session_id,
            AuthSession.revoked_at.is_(None),
        )
        .values(revoked_at=_now(), revocation_reason=reason),
    )
    await session.commit()


async def revoke_all_user_sessions(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    reason: str = "logout_all",
    commit: bool = True,
) -> int:
    result = await session.execute(
        update(AuthSession)
        .where(
            AuthSession.user_id == user_id,
            AuthSession.revoked_at.is_(None),
        )
        .values(revoked_at=_now(), revocation_reason=reason),
    )
    if commit:
        await session.commit()
    else:
        await session.flush()

    return int(result.rowcount or 0)


async def change_password(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    current_password: str,
    new_password: str,
) -> str:
    """
    Change an authenticated user's password after current-password proof.

    Returns the destination email for the post-change security notification.
    """
    result = await session.execute(
        select(UserORM).where(UserORM.id == user_id).with_for_update(),
    )
    user = result.scalar_one_or_none()

    if (
        user is None
        or not user.is_active
        or not verify_password(
            current_password,
            user.hashed_password,
        )
    ):
        raise InvalidCurrentPasswordError

    validate_password_policy(new_password)

    user.hashed_password = hash_password(new_password)
    await session.commit()

    return str(user.email)


def _encode_email_change_token(
    *,
    new_email: str,
) -> str:
    canonical_email = normalize_email(new_email)

    encoded_email = (
        base64.urlsafe_b64encode(canonical_email.encode("utf-8"))
        .decode("ascii")
        .rstrip("=")
    )

    secret = secrets.token_urlsafe(48)
    return f"{secret}.{encoded_email}"


def _decode_email_change_token(
    token: str,
) -> str:
    try:
        secret, separator, encoded_email = token.partition(".")

        if not secret or separator != "." or not encoded_email:
            raise ValueError

        padding = "=" * (-len(encoded_email) % 4)

        decoded = base64.urlsafe_b64decode(encoded_email + padding).decode("utf-8")

        canonical_email = normalize_email(decoded)

        if not canonical_email or len(canonical_email) > 320:
            raise ValueError

        return canonical_email

    except (
        UnicodeDecodeError,
        ValueError,
        TypeError,
    ) as exc:
        raise InvalidActionTokenError from exc


async def create_email_change_token(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    new_email: str,
    expires_in: timedelta,
) -> str:
    """
    Create a single-use email-change confirmation token.

    Only the hash of the complete token is persisted.
    """
    now = _now()

    await session.execute(
        update(IdentityActionToken)
        .where(
            IdentityActionToken.user_id == user_id,
            IdentityActionToken.kind == "email_change",
            IdentityActionToken.consumed_at.is_(None),
        )
        .values(consumed_at=now),
    )

    raw_token = _encode_email_change_token(
        new_email=new_email,
    )

    session.add(
        IdentityActionToken(
            user_id=user_id,
            kind="email_change",
            token_hash=_token_hash(raw_token),
            expires_at=now + expires_in,
        )
    )

    await session.commit()
    return raw_token


async def request_email_change(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    current_password: str,
    new_email: str,
    expires_in: timedelta,
) -> tuple[str, str, str]:
    """
    Reauthenticate and create a pending email-change confirmation.
    """
    result = await session.execute(
        select(UserORM).where(UserORM.id == user_id).with_for_update(),
    )

    user = result.scalar_one_or_none()

    if (
        user is None
        or not user.is_active
        or not verify_password(
            current_password,
            user.hashed_password,
        )
    ):
        raise InvalidCurrentPasswordError

    canonical_email = normalize_email(new_email)

    if canonical_email == user.normalized_email:
        raise EmailAddressUnchangedError

    existing = await session.scalar(
        select(UserORM.id).where(
            UserORM.normalized_email == canonical_email,
            UserORM.id != user_id,
        )
    )

    if existing is not None:
        raise EmailAddressAlreadyInUseError

    old_email = str(user.email)

    token = await create_email_change_token(
        session,
        user_id=user_id,
        new_email=canonical_email,
        expires_in=expires_in,
    )

    return old_email, canonical_email, token


async def confirm_email_change(
    session: AsyncSession,
    *,
    token: str,
) -> tuple[uuid.UUID, str, str]:
    """
    Consume a confirmation token, update canonical identity,
    verify the new address, and revoke existing sessions.
    """
    canonical_email = _decode_email_change_token(token)

    user_id = await consume_action_token(
        session,
        token=token,
        kind="email_change",
    )

    result = await session.execute(
        select(UserORM).where(UserORM.id == user_id).with_for_update(),
    )

    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        await session.rollback()
        raise InvalidActionTokenError

    old_email = str(user.email)

    existing = await session.scalar(
        select(UserORM.id).where(
            UserORM.normalized_email == canonical_email,
            UserORM.id != user_id,
        )
    )

    if existing is not None:
        # The confirmation token has already been consumed.
        await session.commit()
        raise EmailAddressAlreadyInUseError

    try:
        async with session.begin_nested():
            user.email = canonical_email
            user.normalized_email = canonical_email
            user.email_verified_at = _now()
            await session.flush()

    except IntegrityError:
        # A concurrent account claimed this email.
        # Preserve the consumed confirmation token.
        await session.commit()
        raise EmailAddressAlreadyInUseError from None

    await revoke_all_user_sessions(
        session,
        user_id=user_id,
        reason="email_change",
        commit=False,
    )

    await session.commit()

    return user_id, old_email, canonical_email


async def create_action_token(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    kind: str,
    expires_in: timedelta,
) -> str:
    now = _now()
    await session.execute(
        update(IdentityActionToken)
        .where(
            IdentityActionToken.user_id == user_id,
            IdentityActionToken.kind == kind,
            IdentityActionToken.consumed_at.is_(None),
        )
        .values(consumed_at=now),
    )
    raw_token = secrets.token_urlsafe(48)
    session.add(
        IdentityActionToken(
            user_id=user_id,
            kind=kind,
            token_hash=_token_hash(raw_token),
            expires_at=now + expires_in,
        ),
    )
    await session.commit()
    return raw_token


async def consume_action_token(
    session: AsyncSession,
    *,
    token: str,
    kind: str,
) -> uuid.UUID:
    result = await session.execute(
        select(IdentityActionToken)
        .where(
            IdentityActionToken.token_hash == _token_hash(token),
            IdentityActionToken.kind == kind,
        )
        .with_for_update(),
    )
    row = result.scalar_one_or_none()
    now = _now()
    if row is None or row.consumed_at is not None or row.expires_at <= now:
        raise InvalidActionTokenError
    row.consumed_at = now
    await session.flush()
    return row.user_id


async def reset_password_with_token(
    session: AsyncSession,
    *,
    token: str,
    new_password: str,
) -> str:
    """Consume a reset token, change the password, and revoke every session."""
    validate_password_policy(new_password)

    user_id = await consume_action_token(
        session,
        token=token,
        kind="password_reset",
    )
    result = await session.execute(
        select(UserORM).where(UserORM.id == user_id).with_for_update(),
    )
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        await session.rollback()
        raise InvalidActionTokenError
    user.hashed_password = hash_password(new_password)
    await revoke_all_user_sessions(
        session,
        user_id=user_id,
        reason="password_reset",
    )

    return str(user.email)


async def verify_email_with_token(
    session: AsyncSession,
    *,
    token: str,
) -> None:
    """Consume an email-verification token and mark its account verified."""

    user_id = await consume_action_token(
        session,
        token=token,
        kind="email_verification",
    )
    result = await session.execute(
        select(UserORM).where(UserORM.id == user_id).with_for_update(),
    )
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        await session.rollback()
        raise InvalidActionTokenError
    user.email_verified_at = _now()
    await session.commit()


__all__ = [
    "InvalidRefreshTokenError",
    "InvalidActionTokenError",
    "InvalidCurrentPasswordError",
    "EmailAddressAlreadyInUseError",
    "EmailAddressUnchangedError",
    "TokenPair",
    "create_session",
    "change_password",
    "create_email_change_token",
    "request_email_change",
    "confirm_email_change",
    "create_action_token",
    "consume_action_token",
    "is_session_active",
    "list_active_sessions",
    "revoke_all_user_sessions",
    "revoke_other_user_sessions",
    "revoke_session_from_token",
    "revoke_user_session",
    "rotate_refresh_token",
    "reset_password_with_token",
    "verify_email_with_token",
]
