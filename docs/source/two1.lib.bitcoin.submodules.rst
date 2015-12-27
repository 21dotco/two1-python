two1.lib.bitcoin.block
----------------------
This submodule provides the MerkleNode, Block, BlockHeader, and
CompactBlock classes. It allows you to work programmatically with
the individual blocks in the Bitcoin blockchain.

.. automodule:: two1.lib.bitcoin.block
    :members:
    :undoc-members:
    :show-inheritance:

two1.lib.bitcoin.crypto
-----------------------
This submodule provides the PublicKey, PrivateKey, and Signature
classes. It also provides HDPublicKey and HDPrivateKey classes for
working with HD wallets.

.. automodule:: two1.lib.bitcoin.crypto
    :members:
    :undoc-members:
    :show-inheritance:

two1.lib.bitcoin.exceptions
---------------------------
This is a simple submodule that enumerates the different kinds
of exceptions that the ``two1.lib.bitcoin`` module raises.

.. automodule:: two1.lib.bitcoin.exceptions
    :members:
    :undoc-members:
    :show-inheritance:

two1.lib.bitcoin.script
-----------------------
This submodule provides a single Script class that has knowledge
of all Bitcoin opcodes. At the simplest level, it can read in the raw
bytes of a Bitcoin script, parse it, and determine what type of script
it is (P2PKH, P2SH, multi-sig, etc). It also provides capabilities
for building more complex scripts programmatically.

.. automodule:: two1.lib.bitcoin.script
    :members:
    :undoc-members:
    :show-inheritance:

two1.lib.bitcoin.txn
--------------------
This submodule provides Transaction, Coinbase, TransactionInput,
TransactionOutput, and UnspentTransactionOutput classes for building
and parsing Bitcoin transactions and their constituent inputs and
outputs.

.. automodule:: two1.lib.bitcoin.txn
    :members:
    :undoc-members:
    :show-inheritance:

two1.lib.bitcoin.utils
----------------------
This submodule provides functions for accomplishing common tasks
encountered in creating and parsing Bitcoin objects, like turning
difficulties into targets or deserializing and serializing various
kinds of packed byte formats.

.. automodule:: two1.lib.bitcoin.utils
    :members:
    :undoc-members:
    :show-inheritance:
