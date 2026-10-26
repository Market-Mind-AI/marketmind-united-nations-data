class UNDataBaseException(Exception):
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class UNDataClientError(UNDataBaseException):
    """A fonte respondeu, e a resposta não serve: um 4xx que não é 404, uma
    recusa do pedido. Repetir não muda a resposta, então não se repete."""

    def __init__(self, message: str = "UN Data Portal API client error"):
        super().__init__(message=message, status_code=502)


class UNDataTransientError(UNDataBaseException):
    """A fonte está ocupada ou fora do ar (5xx, 429, timeout, rede) e continuou
    assim depois de todas as tentativas. 503 em todos os coletores: quer dizer
    "tente de novo mais tarde", que é exatamente o que vale fazer."""

    def __init__(self, message: str = "UN Data Portal API transient server error"):
        super().__init__(message=message, status_code=503)


class UNDataTimeoutError(UNDataTransientError):
    def __init__(self, message: str = "UN Data Portal API request timed out"):
        super().__init__(message=message)


class UNDataRateLimitError(UNDataTransientError):
    def __init__(self, message: str = "UN Data Portal API rate limit exceeded"):
        super().__init__(message=message)


class UNDataEmptyResponseError(UNDataBaseException):
    """A fonte disse, de forma definitiva, que não tem o dado (404). Numa coleta
    de indicadores isso é uma resposta -- conta como verificação -- e não uma
    falha."""

    def __init__(self, message: str = "UN Data Portal API has no data for this request"):
        super().__init__(message=message, status_code=404)


class IndicatorNotConfiguredError(UNDataBaseException):
    """O pedido nomeia um indicador que este serviço não sabe coletar. É erro de
    quem pediu, o único caso de 4xx de uma coleta -- e o mesmo 422 nos três
    coletores de indicadores."""

    def __init__(self, message: str = "Indicator not configured for collection"):
        super().__init__(message=message, status_code=422)


class ValidationError(UNDataBaseException):
    def __init__(self, message: str = "Validation error"):
        super().__init__(message=message, status_code=422)


class ResourceNotFoundError(UNDataBaseException):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message=message, status_code=404)
