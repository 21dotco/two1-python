"""This is a simple submodule that enumerates the different kinds of exceptions
that the `two1.bitcoin` module raises."""


class DeserializationError(Exception):
    """Generic error for exceptions found while deserializing an object."""
    pass


class InvalidTransactionInputError(DeserializationError):
    """Raised when a TransactionInput object cannot be deserialized."""
    pass


class InvalidCoinbaseInputError(InvalidTransactionInputError):
    """Raised when a CoinbaseInput object cannot be deserialized."""
    pass


class InvalidTransactionOutputError(DeserializationError):
    """Raised when a TransactionOutput object cannot be deserialized."""
    pass


class InvalidTransactionError(DeserializationError):
    """Raised when a Transaction object cannot be deserialized."""
    pass


class InvalidBlockHeaderError(DeserializationError):
    """Raised when a BlockHeader object cannot be deserialized."""
    pass


class InvalidBlockError(DeserializationError):
    """Raised when a Block object cannot be deserialized."""
    pass


class ScriptParsingError(Exception):
    """Raised when parsing an invalid Script."""
    pass


class ScriptTypeError(Exception):
    """Raised when a Script is of an invalid type."""
    pass


class ScriptInterpreterError(Exception):
    """Raised interpreting an invalid Script."""
    pass
