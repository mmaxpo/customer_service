import resend
from enum import Enum

from app.core.config import settings


# -------------------------
# Email Types
# -------------------------
class EmailType(str, Enum):
    NOREPLY = "noreply"
    NOTIFICATION = "notification"
    TEST = "test"


# -------------------------
# Sender Mapping
# -------------------------
EMAIL_FROM_MAP = {
    EmailType.NOREPLY: "Tajeran AI <noreply@tajeran.ai>",
    EmailType.NOTIFICATION: "Tajeran Notifications <notifications@tajeran.ai>",
    EmailType.TEST: "Tajeran AI <noreply@tajeran.ai>",
}


# -------------------------
# Core Email Sender
# -------------------------
def send_email(
    email_type: EmailType,
    to: str,
    subject: str,
    html: str,
    *,
    idempotency_key: str | None = None,
    from_address: str | None = None,
    reply_to: str | None = None,
):
    if email_type not in EMAIL_FROM_MAP:
        raise ValueError(f"Unsupported email type: {email_type}")
    if not settings.RESEND_API_KEY:
        raise RuntimeError("RESEND_API_KEY is not configured")

    resend.api_key = settings.RESEND_API_KEY

    options = {"idempotency_key": idempotency_key} if idempotency_key else None
    payload = {
        "from": from_address or EMAIL_FROM_MAP[email_type],
        "to": to,
        "subject": subject,
        "html": html,
    }
    if reply_to:
        payload["reply_to"] = reply_to
    response = resend.Emails.send(
        payload,
        options=options,
    )

    return response
