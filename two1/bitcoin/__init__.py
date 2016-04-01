# flake8: noqa
"""The bitcoin module within the 21 Bitcoin Library (``two1.bitcoin``) provides
the following functionality:

1. Serialization/deserialization of all Bitcoin data structures:
   blocks and block headers, transactions, scripts, public/private
   keys, and digital signatures. Serialization is achieved via the
   ``bytes()`` method and deserialization is achieved via the
   ``from_bytes()`` static method of each class.
2. Creation of standard scripts: Pay-to-Public-Key-Hash (P2PKH) and
   Pay-to-Script-Hash (P2SH) as well multi-sig script support.
3. Transaction creation, signing, and verification, including multi-sig
   transactions.
4. Standard public/private key generation as well as HD key generation.

In short, you should be able to programmatically manipulate most major
Bitcoin data structures after learning the functions in this module.
"""
from .block import BlockHeader
from .block import Block
from .block import CompactBlock

from .crypto import PrivateKeyBase
from .crypto import PublicKeyBase
from .crypto import PrivateKey
from .crypto import PublicKey
from .crypto import Signature
from .crypto import HDKey
from .crypto import HDPrivateKey
from .crypto import HDPublicKey

from .exceptions import DeserializationError
from .exceptions import InvalidTransactionInputError
from .exceptions import InvalidCoinbaseInputError
from .exceptions import InvalidTransactionOutputError
from .exceptions import InvalidTransactionError
from .exceptions import InvalidBlockHeaderError
from .exceptions import InvalidBlockError
from .exceptions import ScriptParsingError
from .exceptions import ScriptInterpreterError
from .exceptions import ScriptTypeError

from .hash import Hash

from .script import Script

from .txn import TransactionInput
from .txn import TransactionOutput
from .txn import CoinbaseInput
from .txn import UnspentTransactionOutput
from .txn import Transaction
