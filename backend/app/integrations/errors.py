class IntegrationError(Exception):
    pass


class IntegrationTimeoutError(IntegrationError):
    pass


class IntegrationUnavailableError(IntegrationError):
    def __init__(
        self,
        message: str,
        *,
        retry_after_seconds: float | None = None,
    ) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class IntegrationCircuitOpenError(IntegrationUnavailableError):
    pass


class IntegrationProviderError(IntegrationError):
    pass
