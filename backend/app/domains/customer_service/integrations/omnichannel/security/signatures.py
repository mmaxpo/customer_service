from __future__ import annotations

import hashlib
import hmac


class InvalidWebhookSignatureError(Exception):
    pass


def verify_hmac_sha256_signature(
    *,
    secret: str,
    payload: bytes,
    provided_signature: str,
) -> None:
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()

    provided = provided_signature.replace("sha256=", "")

    if not hmac.compare_digest(expected, provided):
        raise InvalidWebhookSignatureError("Invalid webhook signature")
