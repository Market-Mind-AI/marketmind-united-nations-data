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


class IndicatorNotFoundError(UNDataBaseException):
    def __init__(self, message: str = "Indicator not found in catalog"):
        super().__init__(message=message, status_code=404)


class IndicatorNotConfiguredError(UNDataBaseException):
    def __init__(self, message: str = "Indicator not configured for collection"):
        super().__init__(message=message, status_code=422)


class ValidationError(UNDataBaseException):
    def __init__(self, message: str = "Validation error"):
        super().__init__(message=message, status_code=422)


class ResourceNotFoundError(UNDataBaseException):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message=message, status_code=404)
