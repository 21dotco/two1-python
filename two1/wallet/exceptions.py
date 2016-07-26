class WalletError(Exception):
    pass


class WalletSigningError(WalletError):
    pass


class WalletBalanceError(WalletError):
    pass


class UnknownDataProviderError(WalletError):
    pass


class TransactionSendError(WalletError):
    pass


class TxidMismatchError(WalletError):
    pass


class PassphraseError(WalletError):
    pass


class DaemonRunningError(WalletError):
    pass


class DaemonNotRunningError(WalletError):
    pass


class WalletNotLoadedError(WalletError):
    pass


class WalletLockedError(WalletError):
    pass


class UndefinedMethodError(WalletError):
    pass


class AccountCreationError(WalletError):
    pass


class DaemonizerError(WalletError):
    pass


class SatoshiUnitsError(WalletError, TypeError):
    pass


class DustLimitError(WalletError, ValueError):
    pass


class TransactionBuilderException(Exception):
    pass


class OverfullTransactionException(TransactionBuilderException):
    pass
