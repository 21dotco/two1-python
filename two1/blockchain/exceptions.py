import requests


class DataProviderUnavailableError(requests.ConnectionError):
    """Raised when a data provider server cannot be reached."""
    pass


class DataProviderError(Exception):
    """Raised when a data provider encounters an exception."""
    pass
