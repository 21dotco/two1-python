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


class DaemonNotRunningError(WalletError):
    pass


class UndefinedMethodError(WalletError):
    pass
