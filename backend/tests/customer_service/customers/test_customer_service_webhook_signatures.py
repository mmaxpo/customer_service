import hashlib
import hmac

import pytest

from app.domains.customer_service.integrations.omnichannel.security.signatures import (
    InvalidWebhookSignatureError,
    verify_hmac_sha256_signature,
)


def test_verify_hmac_sha256_signature_accepts_valid_signature():
    secret = "super-secret"
    payload = b'{"event":"message"}'

    signature = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()

    verify_hmac_sha256_signature(
        secret=secret,
        payload=payload,
        provided_signature=f"sha256={signature}",
    )


def test_verify_hmac_sha256_signature_rejects_invalid_signature():
    with pytest.raises(InvalidWebhookSignatureError):
        verify_hmac_sha256_signature(
            secret="super-secret",
            payload=b"payload",
            provided_signature="sha256=invalid",
        )
