class WalletError(Exception):
    pass

class WalletSigningError(WalletError):
    pass

class WalletBalanceError(WalletError):
    pass

class TransactionSendError(WalletError):
    pass
