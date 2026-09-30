from __future__ import annotations


class OmnichannelProviderError(Exception):
    retryable: bool = False

    def __init__(self, message: str, *, code: str | None = None):
        super().__init__(message)
        self.code = code


class OmnichannelProviderTransientError(OmnichannelProviderError):
    retryable = True


class OmnichannelProviderPermanentError(OmnichannelProviderError):
    retryable = False
