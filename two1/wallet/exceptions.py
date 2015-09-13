class WalletError(Exception):
    pass

class WalletSigningError(WalletError):
    pass

class WalletBalanceError(WalletError):
    pass

class UnknownTransactionDataProviderError(WalletError):
    pass

class TransactionSendError(WalletError):
    pass

class TxidMismatchError(WalletError):
    pass

class PassphraseError(WalletError):
    pass
