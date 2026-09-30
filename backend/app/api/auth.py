"""HTTP adapter for authentication and identity."""

from __future__ import annotations

import hashlib
import html
from datetime import datetime, timedelta
from typing import Annotated
from urllib.parse import urlencode

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Cookie,
    Depends,
    Form,
    HTTPException,
    Request,
    Response,
)
from pydantic import BaseModel, EmailStr, Field
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.authentication.service import (
    EmailAddressAlreadyInUseError,
    EmailAddressUnchangedError,
    InvalidActionTokenError,
    InvalidCurrentPasswordError,
    InvalidRefreshTokenError,
    change_password,
    confirm_email_change,
    create_action_token,
    create_session,
    is_session_active,
    list_active_sessions,
    revoke_all_user_sessions,
    revoke_other_user_sessions,
    revoke_session_from_token,
    revoke_user_session,
    request_email_change,
    reset_password_with_token,
    rotate_refresh_token,
    verify_email_with_token,
)
from app.core.config import settings
from app.core.http_safety import (
    CSRF_COOKIE,
    RateLimitStore,
    new_csrf_token,
)
from app.core.session import get_db as get_session
from app.identity import (
    LegalAcceptanceRequiredError,
    PasswordPolicyError,
    EmailAlreadyRegisteredError,
    InvalidIdentityTokenError,
    authenticate_user,
    create_user,
    decode_identity_claims,
    decode_identity_token,
    get_user_by_email,
    get_user_by_id,
    normalize_email,
    hash_password,
    verify_password,
)
from app.platform.events.publisher import PlatformEventPublisher

from app.models.schemas import (
    Token,
    UserCreate,
    UserInDB,
    UserRead,
)
from app.services.email_service import EmailType, send_email

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)

SIGNUP_RATE_WINDOW_SECONDS = 60
_signup_rate_store = RateLimitStore(settings.REDIS_URL)

EMAIL_VERIFICATION_RATE_WINDOW_SECONDS = 60
EMAIL_VERIFICATION_RESEND_LIMIT_PER_MINUTE = 5
_verification_rate_store = RateLimitStore(settings.REDIS_URL)

LOGIN_FAILURE_WINDOW_SECONDS = 60
LOGIN_FAILURE_LIMIT = 5
_login_failure_rate_store = RateLimitStore(settings.REDIS_URL)

PASSWORD_RESET_RATE_WINDOW_SECONDS = 60
PASSWORD_RESET_REQUEST_LIMIT_PER_MINUTE = 5
_password_reset_rate_store = RateLimitStore(settings.REDIS_URL)


async def _enforce_signup_rate_limit(
    request: Request,
    *,
    email: str,
) -> None:
    """Rate-limit signup independently by client IP and canonical email."""
    client_ip = request.client.host if request.client else "unknown"
    canonical_email = normalize_email(email)

    ip_digest = hashlib.sha256(client_ip.encode("utf-8")).hexdigest()[:24]

    email_digest = hashlib.sha256(canonical_email.encode("utf-8")).hexdigest()[:24]

    try:
        ip_count = await _signup_rate_store.increment(
            f"signup:ip:{ip_digest}",
            window_seconds=SIGNUP_RATE_WINDOW_SECONDS,
        )
        email_count = await _signup_rate_store.increment(
            f"signup:email:{email_digest}",
            window_seconds=SIGNUP_RATE_WINDOW_SECONDS,
        )
    except RedisError:
        raise HTTPException(
            status_code=503,
            detail="Rate limiting temporarily unavailable",
            headers={"Retry-After": "5"},
        ) from None

    limit = settings.RATE_LIMIT_AUTH_PER_MINUTE

    if ip_count > limit or email_count > limit:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(SIGNUP_RATE_WINDOW_SECONDS)},
        )


async def _enforce_email_verification_resend_rate_limit(
    *,
    user: UserInDB,
) -> None:
    """Throttle verification resends by account and canonical email."""
    canonical_email = normalize_email(str(user.email))

    user_digest = hashlib.sha256(str(user.id).encode("utf-8")).hexdigest()[:24]

    email_digest = hashlib.sha256(canonical_email.encode("utf-8")).hexdigest()[:24]

    try:
        user_count = await _verification_rate_store.increment(
            f"email-verification:user:{user_digest}",
            window_seconds=EMAIL_VERIFICATION_RATE_WINDOW_SECONDS,
        )
        email_count = await _verification_rate_store.increment(
            f"email-verification:email:{email_digest}",
            window_seconds=EMAIL_VERIFICATION_RATE_WINDOW_SECONDS,
        )
    except RedisError:
        raise HTTPException(
            status_code=503,
            detail="Rate limiting temporarily unavailable",
            headers={"Retry-After": "5"},
        ) from None

    if (
        user_count > EMAIL_VERIFICATION_RESEND_LIMIT_PER_MINUTE
        or email_count > EMAIL_VERIFICATION_RESEND_LIMIT_PER_MINUTE
    ):
        raise HTTPException(
            status_code=429,
            detail="Verification resend rate limit exceeded",
            headers={"Retry-After": str(EMAIL_VERIFICATION_RATE_WINDOW_SECONDS)},
        )


async def _enforce_password_reset_request_rate_limit(
    request: Request,
    *,
    email: str,
) -> None:
    """Throttle password-reset requests by client IP and canonical email."""
    client_ip = request.client.host if request.client else "unknown"
    canonical_email = normalize_email(email)

    ip_digest = hashlib.sha256(client_ip.encode("utf-8")).hexdigest()[:24]

    email_digest = hashlib.sha256(canonical_email.encode("utf-8")).hexdigest()[:24]

    try:
        ip_count = await _password_reset_rate_store.increment(
            f"password-reset:ip:{ip_digest}",
            window_seconds=PASSWORD_RESET_RATE_WINDOW_SECONDS,
        )
        email_count = await _password_reset_rate_store.increment(
            f"password-reset:email:{email_digest}",
            window_seconds=PASSWORD_RESET_RATE_WINDOW_SECONDS,
        )
    except RedisError:
        raise HTTPException(
            status_code=503,
            detail="Rate limiting temporarily unavailable",
            headers={"Retry-After": "5"},
        ) from None

    if (
        ip_count > PASSWORD_RESET_REQUEST_LIMIT_PER_MINUTE
        or email_count > PASSWORD_RESET_REQUEST_LIMIT_PER_MINUTE
    ):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(PASSWORD_RESET_RATE_WINDOW_SECONDS)},
        )


def _login_security_keys(
    request: Request,
    *,
    email: str,
) -> tuple[str, str, str, str]:
    """Return non-sensitive fixed-window keys and audit digests."""
    client_ip = request.client.host if request.client else "unknown"
    canonical_email = normalize_email(email)

    ip_digest = hashlib.sha256(client_ip.encode("utf-8")).hexdigest()[:24]

    email_digest = hashlib.sha256(canonical_email.encode("utf-8")).hexdigest()[:24]

    return (
        f"login-failure:ip:{ip_digest}",
        f"login-failure:email:{email_digest}",
        ip_digest,
        email_digest,
    )


async def _enforce_login_failure_backoff(
    request: Request,
    *,
    email: str,
) -> tuple[str, str, str, str]:
    keys = _login_security_keys(
        request,
        email=email,
    )
    ip_key, email_key, _, _ = keys

    try:
        ip_count = await _login_failure_rate_store.current(
            ip_key,
            window_seconds=LOGIN_FAILURE_WINDOW_SECONDS,
        )
        email_count = await _login_failure_rate_store.current(
            email_key,
            window_seconds=LOGIN_FAILURE_WINDOW_SECONDS,
        )
    except RedisError:
        raise HTTPException(
            status_code=503,
            detail="Rate limiting temporarily unavailable",
            headers={"Retry-After": "5"},
        ) from None

    if ip_count >= LOGIN_FAILURE_LIMIT or email_count >= LOGIN_FAILURE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="Too many login attempts",
            headers={"Retry-After": str(LOGIN_FAILURE_WINDOW_SECONDS)},
        )

    return keys


async def _record_login_failure_counts(
    *,
    ip_key: str,
    email_key: str,
) -> bool:
    try:
        ip_count = await _login_failure_rate_store.increment(
            ip_key,
            window_seconds=LOGIN_FAILURE_WINDOW_SECONDS,
        )
        email_count = await _login_failure_rate_store.increment(
            email_key,
            window_seconds=LOGIN_FAILURE_WINDOW_SECONDS,
        )
    except RedisError:
        raise HTTPException(
            status_code=503,
            detail="Rate limiting temporarily unavailable",
            headers={"Retry-After": "5"},
        ) from None

    return ip_count >= LOGIN_FAILURE_LIMIT or email_count >= LOGIN_FAILURE_LIMIT


async def _clear_login_failure_counts(
    *,
    ip_key: str,
    email_key: str,
) -> None:
    try:
        await _login_failure_rate_store.reset(
            ip_key,
            window_seconds=LOGIN_FAILURE_WINDOW_SECONDS,
        )
        await _login_failure_rate_store.reset(
            email_key,
            window_seconds=LOGIN_FAILURE_WINDOW_SECONDS,
        )
    except RedisError:
        raise HTTPException(
            status_code=503,
            detail="Rate limiting temporarily unavailable",
            headers={"Retry-After": "5"},
        ) from None


async def _record_login_event(
    session: AsyncSession,
    *,
    event_type: str,
    user_id,
    ip_digest: str,
    email_digest: str,
    reason: str,
) -> None:
    await PlatformEventPublisher(session).publish(
        user_id=user_id,
        event_type=event_type,
        source="identity.auth",
        payload={
            "method": "password",
            "reason": reason,
            "ip_digest": ip_digest,
            "email_digest": email_digest,
        },
        dispatch=False,
    )


async def _perform_password_login(
    request: Request,
    *,
    email: str,
    password: str,
    session: AsyncSession,
):
    (
        ip_key,
        email_key,
        ip_digest,
        email_digest,
    ) = await _enforce_login_failure_backoff(
        request,
        email=email,
    )

    user = await authenticate_user(
        email,
        password,
        session,
    )

    if user is None:
        candidate = await get_user_by_email(
            email,
            session,
        )

        blocked = await _record_login_failure_counts(
            ip_key=ip_key,
            email_key=email_key,
        )

        await _record_login_event(
            session,
            event_type="identity.login.failed",
            user_id=(candidate.id if candidate is not None else None),
            ip_digest=ip_digest,
            email_digest=email_digest,
            reason=(
                "inactive_account"
                if candidate is not None and not candidate.is_active
                else "invalid_credentials"
            ),
        )

        if blocked:
            raise HTTPException(
                status_code=429,
                detail="Too many login attempts",
                headers={"Retry-After": str(LOGIN_FAILURE_WINDOW_SECONDS)},
            )

        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
        )

    await _clear_login_failure_counts(
        ip_key=ip_key,
        email_key=email_key,
    )

    pair = await create_session(
        session,
        user=user,
        user_agent=request.headers.get("user-agent"),
        ip_address=(request.client.host if request.client else None),
    )

    try:
        await _record_login_event(
            session,
            event_type="identity.login.succeeded",
            user_id=user.id,
            ip_digest=ip_digest,
            email_digest=email_digest,
            reason="authenticated",
        )
    except Exception:
        await revoke_session_from_token(
            session,
            token=pair.access_token,
            reason="login_audit_failed",
        )
        raise

    return pair


REGISTRATION_ACCEPTED_RESPONSE = {"detail": "Registration request accepted."}

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"


class LoginJSON(BaseModel):
    email: str
    password: str


class AuthSessionRead(BaseModel):
    id: str
    current: bool
    user_agent: str | None = None
    ip_address: str | None = None
    created_at: datetime
    last_used_at: datetime
    expires_at: datetime


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(
        min_length=1,
        max_length=1024,
    )
    new_password: str = Field(
        min_length=12,
        max_length=1024,
    )


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str = Field(min_length=32, max_length=512)
    new_password: str = Field(min_length=12, max_length=1024)


class EmailChangeRequest(BaseModel):
    current_password: str = Field(
        min_length=1,
        max_length=1024,
    )
    new_email: EmailStr


class ActionTokenConfirm(BaseModel):
    token: str = Field(min_length=32, max_length=512)


async def _record_email_change_event(
    session: AsyncSession,
    *,
    event_type: str,
    user_id,
    old_email: str,
    new_email: str,
) -> None:
    old_digest = hashlib.sha256(normalize_email(old_email).encode("utf-8")).hexdigest()[
        :24
    ]

    new_digest = hashlib.sha256(normalize_email(new_email).encode("utf-8")).hexdigest()[
        :24
    ]

    await PlatformEventPublisher(session).publish(
        user_id=user_id,
        event_type=event_type,
        source="identity.auth",
        payload={
            "old_email_digest": old_digest,
            "new_email_digest": new_digest,
        },
        dispatch=False,
    )


def _send_security_notification(
    *,
    to: str,
    subject: str,
    message: str,
) -> None:
    send_email(
        email_type=EmailType.NOREPLY,
        to=to,
        subject=subject,
        html=f"<p>{html.escape(message)}</p>",
    )


def _send_action_email(
    *,
    to: str,
    subject: str,
    path: str,
    token: str,
) -> None:
    query = urlencode({"token": token})
    link = f"{settings.WEB_APP_URL.rstrip('/')}/{path.lstrip('/')}?{query}"
    safe_link = html.escape(link, quote=True)
    send_email(
        email_type=EmailType.NOREPLY,
        to=to,
        subject=subject,
        html=f'<p><a href="{safe_link}">{html.escape(subject)}</a></p>',
    )


def get_token(
    request: Request,
    access_cookie: str | None = Cookie(
        default=None,
        alias=ACCESS_COOKIE,
    ),
) -> str | None:
    """Prefer Authorization header; fall back to access-token cookie."""

    auth = request.headers.get("authorization")

    if auth and auth.lower().startswith("bearer "):
        return auth.split(
            " ",
            1,
        )[1].strip()

    return access_cookie


async def get_current_user(
    token: str | None = Depends(get_token),
    session: AsyncSession = Depends(get_session),
) -> UserInDB:
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        claims = decode_identity_claims(
            token,
            expected_type="access",
        )
        uid, email = decode_identity_token(token)
    except InvalidIdentityTokenError:
        raise HTTPException(
            status_code=401,
            detail="Invalid token_control",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    user = await (
        get_user_by_id(
            uid,
            session,
        )
        if uid
        else get_user_by_email(
            email or "",
            session,
        )
    )

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=401,
            detail="Invalid token_control",
            headers={"WWW-Authenticate": "Bearer"},
        )

    session_id = claims.get("sid")

    if session_id is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not await is_session_active(
        session,
        session_id=str(session_id),
        user_id=user.id,
    ):
        raise HTTPException(
            status_code=401,
            detail="Session is no longer active",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


@router.post(
    "/signup",
    response_model=dict[str, str],
    status_code=201,
)
async def signup(
    data: UserCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    await _enforce_signup_rate_limit(
        request,
        email=str(data.email),
    )

    try:
        await create_user(
            data,
            session,
        )
    except LegalAcceptanceRequiredError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from None
    except PasswordPolicyError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from None
    except EmailAlreadyRegisteredError:
        return REGISTRATION_ACCEPTED_RESPONSE.copy()

    return REGISTRATION_ACCEPTED_RESPONSE.copy()


def _token_response(
    *,
    access_token: str,
    refresh_token: str,
) -> Response:
    payload = Token(
        access_token=access_token,
        token_type="bearer",
        refresh_token=refresh_token,
    )

    response = Response(
        content=payload.model_dump_json(),
        media_type="application/json",
    )

    response.set_cookie(
        ACCESS_COOKIE,
        access_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.ACCESS_COOKIE_MAX_AGE,
        path="/",
    )

    response.set_cookie(
        CSRF_COOKIE,
        new_csrf_token(),
        httponly=False,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.REFRESH_COOKIE_MAX_AGE,
        path="/",
    )

    response.set_cookie(
        REFRESH_COOKIE,
        refresh_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.REFRESH_COOKIE_MAX_AGE,
        path="/",
    )

    return response


@router.post(
    "/login",
    response_model=Token,
)
async def login_for_access_token(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    content_type = (request.headers.get("content-type") or "").lower()

    if content_type.startswith("application/json"):
        try:
            raw_data = await request.json()
            data = LoginJSON.model_validate(raw_data)
        except Exception as exc:
            from json import JSONDecodeError

            from pydantic import ValidationError

            if isinstance(exc, ValidationError):
                detail = []

                for error in exc.errors():
                    item = dict(error)
                    item["loc"] = [
                        "body",
                        *error.get("loc", ()),
                    ]
                    detail.append(item)

                raise HTTPException(
                    status_code=422,
                    detail=detail,
                ) from exc

            if isinstance(exc, JSONDecodeError):
                raise HTTPException(
                    status_code=422,
                    detail=[
                        {
                            "type": "json_invalid",
                            "loc": ["body"],
                            "msg": "Invalid JSON",
                            "input": None,
                        }
                    ],
                ) from exc

            raise

        email = data.email
        password = data.password

    else:
        form = await request.form()

        email = form.get("email")
        password = form.get("password")

        if not email or not password:
            raise HTTPException(
                status_code=422,
                detail=("email and password are required"),
            )

    pair = await _perform_password_login(
        request,
        email=str(email),
        password=str(password),
        session=session,
    )

    return _token_response(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
    )


@router.post(
    "/login-form",
    response_model=Token,
)
async def login_Swagger(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    session: AsyncSession = Depends(get_session),
):
    pair = await _perform_password_login(
        request,
        email=email,
        password=password,
        session=session,
    )

    return _token_response(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
    )


@router.post(
    "/refresh",
    response_model=Token,
)
async def refresh_token(
    refresh_cookie: str | None = Cookie(
        default=None,
        alias=REFRESH_COOKIE,
    ),
    session: AsyncSession = Depends(get_session),
):
    if not refresh_cookie:
        raise HTTPException(
            status_code=401,
            detail=("Missing refresh token_control"),
        )

    try:
        claims = decode_identity_claims(
            refresh_cookie,
            expected_type="refresh",
        )
        uid = str(claims.get("uid")) if claims.get("uid") else None
        email = str(claims.get("sub")) if claims.get("sub") else None
    except InvalidIdentityTokenError:
        raise HTTPException(
            status_code=401,
            detail=("Invalid refresh token_control"),
        ) from None

    user = await (
        get_user_by_id(
            uid,
            session,
        )
        if uid
        else get_user_by_email(
            email or "",
            session,
        )
    )

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="User not found",
        )

    try:
        pair = await rotate_refresh_token(
            session,
            token=refresh_cookie,
            user=user,
        )
    except InvalidRefreshTokenError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or already used refresh token",
        ) from None

    return _token_response(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
    )


def _current_access_session_id(
    token: str | None,
) -> str:
    """Return the session id from a validated access-token shape."""
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        claims = decode_identity_claims(
            token,
            expected_type="access",
        )
        session_id = claims.get("sid")

        if session_id is None:
            raise InvalidIdentityTokenError("Access token has no session")

        return str(session_id)

    except InvalidIdentityTokenError:
        raise HTTPException(
            status_code=401,
            detail="Invalid access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None


@router.post(
    "/logout",
    status_code=204,
)
async def logout(
    request: Request,
    refresh_cookie: str | None = Cookie(
        default=None,
        alias=REFRESH_COOKIE,
    ),
    session: AsyncSession = Depends(get_session),
) -> Response:
    token = refresh_cookie or get_token(request)
    # Presence leases are connection/session scoped, so logging out one tab
    # cannot mark another authenticated session offline.
    if token:
        try:
            claims = decode_identity_claims(token, expected_type="refresh")
        except InvalidIdentityTokenError:
            try:
                claims = decode_identity_claims(token, expected_type="access")
            except InvalidIdentityTokenError:
                claims = None
        if claims and claims.get("sid"):
            from app.platform.realtime.presence import PresenceLease
            await PresenceLease().release_session(str(claims["sid"]))
    await revoke_session_from_token(
        session,
        token=token,
    )
    response = Response(status_code=204)

    response.delete_cookie(
        ACCESS_COOKIE,
        path="/",
    )

    response.delete_cookie(
        REFRESH_COOKIE,
        path="/",
    )
    response.delete_cookie(CSRF_COOKIE, path="/")

    return response


@router.get(
    "/sessions",
    response_model=list[AuthSessionRead],
)
async def get_active_sessions(
    token: str | None = Depends(get_token),
    current_user: UserInDB = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[AuthSessionRead]:
    current_session_id = _current_access_session_id(token)

    rows = await list_active_sessions(
        session,
        user_id=current_user.id,
    )

    return [
        AuthSessionRead(
            id=str(row.id),
            current=(str(row.id) == current_session_id),
            user_agent=row.user_agent,
            ip_address=row.ip_address,
            created_at=row.created_at,
            last_used_at=row.last_used_at,
            expires_at=row.expires_at,
        )
        for row in rows
    ]


@router.delete(
    "/sessions/{session_id}",
    status_code=204,
)
async def revoke_selected_session(
    session_id: str,
    current_user: UserInDB = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Response:
    revoked = await revoke_user_session(
        session,
        user_id=current_user.id,
        session_id=session_id,
    )

    if not revoked:
        raise HTTPException(
            status_code=404,
            detail="Session not found",
        )

    return Response(status_code=204)


@router.post(
    "/sessions/logout-others",
    status_code=204,
)
async def logout_other_sessions(
    token: str | None = Depends(get_token),
    current_user: UserInDB = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Response:
    current_session_id = _current_access_session_id(token)

    await revoke_other_user_sessions(
        session,
        user_id=current_user.id,
        current_session_id=current_session_id,
    )

    return Response(status_code=204)


@router.post(
    "/logout-all",
    status_code=204,
)
async def logout_all(
    current_user: UserInDB = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Response:
    await revoke_all_user_sessions(
        session,
        user_id=current_user.id,
    )
    response = Response(status_code=204)
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")
    return response


@router.post("/email-change/request", status_code=202)
async def request_current_email_change(
    data: EmailChangeRequest,
    background_tasks: BackgroundTasks,
    current_user: UserInDB = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    try:
        old_email, new_email, token = await request_email_change(
            session,
            user_id=current_user.id,
            current_password=data.current_password,
            new_email=str(data.new_email),
            expires_in=timedelta(
                minutes=settings.EMAIL_VERIFICATION_EXPIRE_MINUTES,
            ),
        )
    except InvalidCurrentPasswordError:
        raise HTTPException(
            status_code=400,
            detail="Current password is incorrect",
        ) from None
    except EmailAddressUnchangedError:
        raise HTTPException(
            status_code=400,
            detail="New email must be different from current email",
        ) from None
    except EmailAddressAlreadyInUseError:
        raise HTTPException(
            status_code=409,
            detail="Email address is already in use",
        ) from None

    await _record_email_change_event(
        session,
        event_type="identity.email_change.requested",
        user_id=current_user.id,
        old_email=old_email,
        new_email=new_email,
    )

    background_tasks.add_task(
        _send_action_email,
        to=new_email,
        subject="Confirm your new Tajeran email",
        path="confirm-email-change",
        token=token,
    )

    background_tasks.add_task(
        _send_security_notification,
        to=old_email,
        subject="Tajeran email change requested",
        message=(
            "A request was made to change the email address on your "
            "Tajeran account. If you did not make this request, "
            "contact support immediately."
        ),
    )

    return {"detail": "Email change confirmation sent."}


@router.post("/email-change/confirm", status_code=204)
async def confirm_current_email_change(
    data: ActionTokenConfirm,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> Response:
    try:
        user_id, old_email, new_email = await confirm_email_change(
            session,
            token=data.token,
        )
    except InvalidActionTokenError:
        raise HTTPException(
            status_code=400,
            detail="Invalid, expired, or already used email-change token",
        ) from None
    except EmailAddressAlreadyInUseError:
        raise HTTPException(
            status_code=409,
            detail="Email address is already in use",
        ) from None

    await _record_email_change_event(
        session,
        event_type="identity.email_change.confirmed",
        user_id=user_id,
        old_email=old_email,
        new_email=new_email,
    )

    background_tasks.add_task(
        _send_security_notification,
        to=old_email,
        subject="Your Tajeran email was changed",
        message=(
            "The email address on your Tajeran account was changed. "
            "All previous sessions were signed out. If you did not "
            "make this change, contact support immediately."
        ),
    )

    background_tasks.add_task(
        _send_security_notification,
        to=new_email,
        subject="Your Tajeran email was changed",
        message=(
            "Your new Tajeran email address is confirmed. "
            "Please sign in again using this email address."
        ),
    )

    return Response(status_code=204)


@router.post("/password-change", status_code=204)
async def change_current_password(
    data: PasswordChangeRequest,
    background_tasks: BackgroundTasks,
    current_user: UserInDB = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Response:
    try:
        destination = await change_password(
            session,
            user_id=current_user.id,
            current_password=data.current_password,
            new_password=data.new_password,
        )
    except InvalidCurrentPasswordError:
        raise HTTPException(
            status_code=400,
            detail="Current password is incorrect",
        ) from None
    except PasswordPolicyError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from None

    background_tasks.add_task(
        _send_security_notification,
        to=destination,
        subject="Your Tajeran password was changed",
        message=(
            "Your Tajeran password was changed. "
            "If you did not make this change, contact support immediately."
        ),
    )

    return Response(status_code=204)


@router.post("/password-reset/request", status_code=202)
async def request_password_reset(
    data: PasswordResetRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    await _enforce_password_reset_request_rate_limit(
        request,
        email=str(data.email),
    )

    user = await get_user_by_email(str(data.email), session)
    if user is not None and user.is_active:
        token = await create_action_token(
            session,
            user_id=user.id,
            kind="password_reset",
            expires_in=timedelta(
                minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES,
            ),
        )
        background_tasks.add_task(
            _send_action_email,
            to=user.email,
            subject="Reset your Tajeran password",
            path="reset-password",
            token=token,
        )
    return {"detail": "If the account exists, reset instructions were sent."}


@router.post("/password-reset/confirm", status_code=204)
async def confirm_password_reset(
    data: PasswordResetConfirm,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> Response:
    try:
        destination = await reset_password_with_token(
            session,
            token=data.token,
            new_password=data.new_password,
        )
    except PasswordPolicyError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from None
    except InvalidActionTokenError:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired password-reset token",
        ) from None

    background_tasks.add_task(
        _send_security_notification,
        to=destination,
        subject="Your Tajeran password was reset",
        message=(
            "Your Tajeran password was reset. "
            "All previous sessions were signed out. "
            "If you did not make this change, contact support immediately."
        ),
    )

    return Response(status_code=204)


@router.post("/email-verification/request", status_code=202)
async def request_email_verification(
    current_user: UserInDB = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    if current_user.email_verified_at is None:
        await _enforce_email_verification_resend_rate_limit(
            user=current_user,
        )

        token = await create_action_token(
            session,
            user_id=current_user.id,
            kind="email_verification",
            expires_in=timedelta(
                minutes=settings.EMAIL_VERIFICATION_EXPIRE_MINUTES,
            ),
        )
        try:
            await run_in_threadpool(
                _send_action_email,
                to=current_user.email,
                subject="Verify your Tajeran email",
                path="verify-email",
                token=token,
            )
        except Exception:
            raise HTTPException(
                status_code=503,
                detail="Verification email could not be sent. Please try again shortly.",
            ) from None
    return {"detail": "Verification instructions were sent."}


@router.post("/email-verification/confirm", status_code=204)
async def confirm_email_verification(
    data: ActionTokenConfirm,
    session: AsyncSession = Depends(get_session),
) -> Response:
    try:
        await verify_email_with_token(
            session,
            token=data.token,
        )
    except InvalidActionTokenError:
        raise HTTPException(
            status_code=400,
            detail=(
                "Verification link is invalid, expired, or already used. "
                "Request a new verification email."
            ),
        ) from None

    return Response(status_code=204)


async def get_current_verified_user(
    current_user: Annotated[
        UserInDB,
        Depends(get_current_user),
    ],
) -> UserInDB:
    """
    Require verified email for workspace and product access.

    Test-only lightweight fake principals remain compatible because
    production authentication returns UserInDB.
    """
    if isinstance(current_user, UserInDB) and current_user.email_verified_at is None:
        raise HTTPException(
            status_code=403,
            detail={"code": "email_verification_required"},
        )

    return current_user


async def get_current_active_user(
    current_user: Annotated[
        UserInDB,
        Depends(get_current_user),
    ],
) -> UserInDB:
    if not current_user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Inactive user",
        )

    return current_user


@router.get(
    "/me",
    response_model=UserRead,
)
async def read_current_user(
    current_user: UserInDB = Depends(get_current_active_user),
):
    return UserRead.model_validate(
        current_user,
        from_attributes=True,
    )


# Compatibility exports.
#
# Existing application/tests may import these helpers from app.api.auth.
# Ownership now lives in app.identity while the old import surface remains
# available during this boundary migration.
__all__ = [
    "ACCESS_COOKIE",
    "REFRESH_COOKIE",
    "authenticate_user",
    "get_current_active_user",
    "get_current_user",
    "get_current_verified_user",
    "get_token",
    "get_user_by_email",
    "get_user_by_id",
    "hash_password",
    "router",
    "verify_password",
]
