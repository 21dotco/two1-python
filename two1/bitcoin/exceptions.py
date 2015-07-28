class DeserializationError(Exception):
    pass

class InvalidTransactionInputError(DeserializationError):
    pass

class InvalidCoinbaseInputError(InvalidTransactionInputError):
    pass

class InvalidTransactionOutputError(DeserializationError):
    pass

class InvalidTransactionError(DeserializationError):
    pass

class InvalidBlockHeaderError(DeserializationError):
    pass

class InvalidBlockError(DeserializationError):
    pass

class ParsingError(Exception):
    pass

class ScriptTypeError(Exception):
    pass
