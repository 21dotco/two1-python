The 21 Bitcoin Library (``two1.bitcoin``)
=============================================
The bitcoin module within the 21 Bitcoin Library (``two1.bitcoin``) provides
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

Quickstart
==========
We will illustrate the use of the ``two1.bitcoin`` module by showing
how to parse, create, and sign a transaction.

Parsing a transaction
---------------------
Transactions are the most likely starting place for this module. A
transaction can be deserialized from a hex string. For example, this
`transaction <https://blockchain.info/tx/039fc554371f9381376b3ea7a3f22009709f05a993fa90a919ac73c1713bba3b>`_
can be deserialized as follows::

  import requests

  from two1.bitcoin.txn import Transaction

  tx_hex = requests.request("GET", "https://blockchain.info/rawtx/039fc554371f9381376b3ea7a3f22009709f05a993fa90a919ac73c1713bba3b?format=hex").text

  txn = Transaction.from_hex(tx_hex)

  print("txid: %s" % (txn.hash))
  print("Num inputs: %d" % (txn.num_inputs))
  print("Num outputs: %d" % (txn.num_outputs))

which gives the following::

  txid: 039fc554371f9381376b3ea7a3f22009709f05a993fa90a919ac73c1713bba3b
  Num inputs: 5
  Num outputs: 2

We can iterate over the inputs and outputs and print out the addresses associated with each::

  for i, inp in enumerate(txn.inputs):
    print("Input %d: %r" % (i, inp.get_addresses()))

  for i, out in enumerate(txn.outputs):
    print("Output %d: %r" % (i, out.get_addresses()))

Results::

  Input 0: ['18ganSKbBJcHi82mqLmY5UKHG9nxYZWZDU']
  Input 1: ['18ganSKbBJcHi82mqLmY5UKHG9nxYZWZDU']
  Input 2: ['18ganSKbBJcHi82mqLmY5UKHG9nxYZWZDU']
  Input 3: ['18ganSKbBJcHi82mqLmY5UKHG9nxYZWZDU']
  Input 4: ['18ganSKbBJcHi82mqLmY5UKHG9nxYZWZDU']
  Output 0: ['137KzxStaf6vw5yGujViK3Tkigoix9N3v7']
  Output 1: ['1YBnESCmM3irLX9Z8zCaKvCorJwwCrGtv']

For the outputs, we can inspect the value::

  for i, inp in enumerate(txn.inputs):
      print("Input %d: %r" % (i, inp.get_addresses()))

  for i, out in enumerate(txn.outputs):
      print("Output %d: %r, %d satoshis" % (i, out.get_addresses(), out.value))

which gives::

  Input 0: ['18ganSKbBJcHi82mqLmY5UKHG9nxYZWZDU']
  Input 1: ['18ganSKbBJcHi82mqLmY5UKHG9nxYZWZDU']
  Input 2: ['18ganSKbBJcHi82mqLmY5UKHG9nxYZWZDU']
  Input 3: ['18ganSKbBJcHi82mqLmY5UKHG9nxYZWZDU']
  Input 4: ['18ganSKbBJcHi82mqLmY5UKHG9nxYZWZDU']
  Output 0: ['137KzxStaf6vw5yGujViK3Tkigoix9N3v7'], 100000 satoshis
  Output 1: ['1YBnESCmM3irLX9Z8zCaKvCorJwwCrGtv'], 23100 satoshis

The transaction can be serialized to either hex or bytes::

  print(txn.to_hex())
  txn_bytes = bytes(txn)

While this shows how to serialize a transaction, serialization and
deserialization is consistent amongst all classes. Serialization is
achieved via the ``bytes()`` method and deserialization is achieved via
the ``from_bytes()`` static method of each class.

Creating a transaction
----------------------
A transaction can be created from scratch by creating and inserting
inputs and outputs. As outputs don't require any signing, let's start
by creating the first output in the above transacion::

  from two1.bitcoin.txn import TransactionOutput
  from two1.bitcoin.script import Script
  from two1.bitcoin.utils import address_to_key_hash
  from two1.bitcoin.utils import bytes_to_str

  address = '137KzxStaf6vw5yGujViK3Tkigoix9N3v7'
  _, hash160 = address_to_key_hash(address)
  out_script = Script.build_p2pkh(hash160)
  out1 = TransactionOutput(value=100000, script=out_script)

  # Print the script
  print("%s" % (out_script))

  # Print the address
  print("Addresses = %r" % (out1.get_addresses()))

  # Print the value
  print("Value: %d" % (out1.value))

  # Serialize
  out1_bytes = bytes(out1)
  print(bytes_to_str(out1_bytes))

Results::
  
  OP_DUP OP_HASH160 0x17229b6b4ac45e1a73a6a64fedd9f7d4dab4333e OP_EQUALVERIFY OP_CHECKSIG
  Addresses = ['137KzxStaf6vw5yGujViK3Tkigoix9N3v7']
  Value: 100000
  a0860100000000001976a91417229b6b4ac45e1a73a6a64fedd9f7d4dab4333e88ac

In the above example, we had to extract the HASH160 of the
address. The utility function ``address_to_key_hash`` allowed us to do
that. Using that, we built a Pay-to-Public-Key Hash script using
``Script.build_p2pkh()`` which was the first line of the output. We then
created the transaction output, inspected the addresses and saw that
we got the same address we input, inspected the value and finally
serialized the output.

An output by itself is relatively useless without an input as the
input provides the funds to fund the transaction. However, to create
an input, we need to prove we have ownership of the key that contains
the input funds. Since we do not have the private key associated with
the inputs in the above transaction, we will create a new key pair and
sign a fake input. To do this, we will use the
``two1.bitcoin.crypto`` module::

  from two1.bitcoin.crypto import PrivateKey

  private_key = PrivateKey.from_random()

  # Get the public key and address associated with this address
  print("Address: %s" % private_key.public_key.address())

Results (this will be different for everyone as we are generating a random key)::

  Address: 13wBf3z3rshFGWDpMCyBowzCGxWNVnXXyL

A complete example: creating and signing a transaction
------------------------------------------------------
Let's put it all together::

  from two1.bitcoin.crypto import PrivateKey
  from two1.bitcoin.hash import Hash
  from two1.bitcoin.txn import TransactionInput
  from two1.bitcoin.txn import TransactionOutput
  from two1.bitcoin.txn import Transaction
  from two1.bitcoin.script import Script
  from two1.bitcoin.utils import address_to_key_hash
  from two1.bitcoin.utils import bytes_to_str

  # We use a random private key.
  # If you wanted to use a real one, you'd import the wallet
  # and do wallet.get_private_key(utxo_addr)
  private_key = PrivateKey.from_random()

  # Get the public key and address associated with this address
  print("Address: %s" % private_key.public_key.address())

  # Create a P2PKH as the UTXO from which we're spending based on
  # the private key we just generated. This will not be valid to
  # send to the network, but shows how to sign an input.
  hash160 = private_key.public_key.hash160()
  utxo_pubkey_script = Script.build_p2pkh(hash160)

  # Create a transaction input using an empty script
  out_txid = Hash("0000000000000000000000000000000000000000000000000000000000000000")
  inp = TransactionInput(outpoint=out_txid,
                         outpoint_index=0,
                         script=Script(),
                         sequence_num=0xffffffff)

  # Create the output
  address = '137KzxStaf6vw5yGujViK3Tkigoix9N3v7'
  _, hash160 = address_to_key_hash(address)
  out_script = Script.build_p2pkh(hash160)
  out = TransactionOutput(value=100000, script=out_script)

  # Now let's create a transaction
  txn = Transaction(version=Transaction.DEFAULT_TRANSACTION_VERSION,
                    inputs=[inp],
                    outputs=[out],
                    lock_time=0)

  # Sign our input
  txn.sign_input(input_index=0,
                 hash_type=Transaction.SIG_HASH_ALL,
                 private_key=private_key,
                 sub_script=utxo_pubkey_script)

  # Print out signature script
  print("\nSignature script: %s" % inp.script)

  # And now the serialized transaction
  print("\nTransaction:\n%s" % txn.to_hex())
  print("\ntxid: %s" % txn.hash)

  # verify the transaction input
  verified = txn.verify_input_signature(input_index=0,
                                        sub_script=utxo_pubkey_script)
  print("\nInput verified? %r" % verified)
  
And we get something like the following.::
  
  Address: 1De2UioE5RmT1VtLkhM3ffzbRB58TwjNmM

  Signature script: 0x3045022100f9a25ff8a367e0e100519d87e8f45fb4808e26388e5c8b79642627e277dee58d022031a06596e21d977dde0e87152cd17fc9345a88a772ad30034dabfb6c974a3ad401 0x026336febca03a09c4d0db1179ea22ddce435437e3a4df0bf962f50189855a2910

  Transaction:
  01000000013bba3b71c173ac19a990fa93a9059f700920f2a3a73e6b3781931f3754c59f03000000006b483045022100f9a25ff8a367e0e100519d87e8f45fb4808e26388e5c8b79642627e277dee58d022031a06596e21d977dde0e87152cd17fc9345a88a772ad30034dabfb6c974a3ad40121026336febca03a09c4d0db1179ea22ddce435437e3a4df0bf962f50189855a2910ffffffff01a0860100000000001976a91417229b6b4ac45e1a73a6a64fedd9f7d4dab4333e88ac00000000

  txid: 1c91fdb94754dde1c1e80eff6e9e243df420a1dc6cde041a1022b51ebc34acf2

  Input verified? True

As above, your exact results will be different since we're generating
random private keys.

Note that while this transaction could not be submitted to the Bitcoin
network (since the UTXO we referenced doesn't exist), we were able to
create a single input/single output transaction, sign the input,
verify it, and serialize the entire transaction into a form that
`could` be submitted. To see how to broadcast a raw transaction, see
``provider.broadcast_transaction`` in `two1.blockchain <../../learn/21-lib-blockchain>`_.

If you want to do this example with a proper UTXO, replace the line
referencing the ``private_key`` with
``wallet.get_private_key(utxo_addr)``. This is an example of using the
``two1.wallet`` module programmatically. See also the `Bitcoin
Notary Public <../../learn/bitcoin-notary-public>`_ tutorial for a
worked example.


``two1.bitcoin``: module contents
=====================================
The ``two1.bitcoin`` module is organized into the following submodules:
   
.. toctree::

   two1.bitcoin.submodules
