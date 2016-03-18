from collections import namedtuple

PURPOSE_CONSTANT = 0x8000002C
BITCOIN_MAINNET = 0x80000000
BITCOIN_TESTNET = 0x80000001

AccountType = namedtuple("AccountType", "account_derivation_prefix")

account_types = {'BIP32':               AccountType(account_derivation_prefix="m/"),
                 'Hive':                AccountType(account_derivation_prefix="m/0'"),
                 'BreadWallet':         AccountType(account_derivation_prefix="m/0'/0/0"),
                 'Mycelium':            AccountType(account_derivation_prefix="m/44'/0'/0'"),
                 'BIP44Testnet':        AccountType(account_derivation_prefix="m/44'/1'"),
                 'BIP44BitcoinMainnet': AccountType(account_derivation_prefix="m/44'/0'")}

# For now that's it. In theory, we could do all of the registered coin-types
# http://doc.satoshilabs.com/slips/slip-0044.html
