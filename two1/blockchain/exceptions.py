"""This is a simple submodule that enumerates the different kinds of exceptions
that the `two1.blockchain` module raises."""


class DataProviderUnavailableError(Exception):
    """Raised when a data provider server cannot be reached."""
    pass


class DataProviderError(Exception):
    """Raised when a data provider encounters an exception."""
    pass
