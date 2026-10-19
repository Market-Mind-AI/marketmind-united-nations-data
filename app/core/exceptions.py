class UNDataBaseException(Exception):
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class UNDataClientError(UNDataBaseException):
    def __init__(self, message: str = "UN Data Portal API client error"):
        super().__init__(message=message, status_code=502)


class UNDataTimeoutError(UNDataBaseException):
    def __init__(self, message: str = "UN Data Portal API request timed out"):
        super().__init__(message=message, status_code=504)


class UNDataTransientError(UNDataBaseException):
    """A transient upstream failure (HTTP 5xx) worth retrying — the UN Data
    Portal API returns intermittent 500/502/503/504 under load. Distinct from
    UNDataClientError (non-retryable, e.g. 4xx) so the retry loop can back off
    and try again instead of failing the whole collection on a single blip."""

    def __init__(self, message: str = "UN Data Portal API transient server error"):
        super().__init__(message=message, status_code=503)


class IndicatorNotConfiguredError(UNDataBaseException):
    def __init__(self, message: str = "Indicator not configured for collection"):
        super().__init__(message=message, status_code=422)


class ValidationError(UNDataBaseException):
    def __init__(self, message: str = "Validation error"):
        super().__init__(message=message, status_code=422)


class ResourceNotFoundError(UNDataBaseException):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message=message, status_code=404)
