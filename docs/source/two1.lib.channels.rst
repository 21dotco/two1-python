The 21 Payment Channels Client Library
======================================

Overview
--------

The payment channel protocol allows for fast, high-volume payments to
occur from one party (a customer) to another (a merchant) in a
trust-less manner. There are further derivations that allow for payments
to occur both ways (bi-directionally); however, this implementation
covers the unidirectional case.

Payment channels consist of negotiating an ``open`` stage, an active
``ready`` stage where many payments can be made, and a ``closing`` stage
where a final transaction is broadcast.

.. figure:: https://assets.21.co/two1docs/PCs.png
   :alt: Payment Channels Protocol

Channel open
^^^^^^^^^^^^

1. **Customer requests merchants public key; merchant responds with
   fresh (compressed) public key.**

   ::

       Merchant pubkey:
           02d79987da792634d39f5c14741774311ab9421d2775c2bc9a608489de9277aa83

2. **Customer creates an
   `CLTV-style <https://github.com/bitcoin/bips/blob/master/bip-0065.mediawiki>`__
   refund/payment transaction and a deposit that pays to its redeem
   script.**

   ::

       Redeem script instructions:
           if
             <merchant pubkey> checksigverify
           else
             <timestamp> checklocktimeverify drop
           endif
           <customer pubkey> checksig

       Redeem script hex:
           632102d79987da792634d39f5c14741774311ab9421d2775c2bc9a608489de9277aa83ad670464da7156b175682103a5c2c5fe32a8ae5a8f67a314042cdd9eb33be822c6214d46109654ee269519faac

       Redeem script address:
           3MuV5ndotUyvgMc4cq73JPHwBEVMEgHUSa

   This transaction will always require a signature by the customer (the
   last line in the script); however, the transaction can be spent by
   either: (1) adding a signature from the merchant, or (2) if the value
   of the nLockTime field exceeds the timestamp (aka the transaction can
   be spent).

   Next we create a deposit that pays into the hash of the above script
   (pay-to-script-hash). In this example we want to open a channel for
   ``100,000 satoshis`` - notice that we pay a bit more than that to
   allow for transaction fees on the way back.

   ::

       Deposit transaction layout:
           input(s):
             - <previous tx> <index> | <script sig> <script pubkey>
           nLockTime 0
           outputs:
             - dup hash160 <customer change address> equalverify checksig
             - hash160 <redeem script address> equal [111,000 satoshis]

       Deposit transaction hex:
         0100000001cd7edc5280aa3bf6120c98a587fa9691f843447905d03212dc1487e35c2b1993000000006b483045022100a15a21215db068aae693b5ea2344e112f1c460ef41dc5716724f5a7d020189e002202681e8833c69b248c999be2168be0c722314031979c10b2f00a1b8a5e7de8785012103d567c82c4578080bc07e695e660d10d38d8ebba7d24f3e4888ff439015491979ffffffff028ccc0800000000001976a914206acc7cc7b959ec8d9466cddaaadf4a2fd1e7b088ac98b101000000000017a914ddbe2dc0ce28de6648b2980b9bd705ca608fe7a18700000000

   How do we spend these transactions? Well in terms of a refund, you'll
   notice that the CLTV-style refund/payment transaction can behave in
   two different ways. The ``OP_IF`` opcode will branch depending on
   whether the value immediately preceeding it is ``0`` or ``1``. In the
   case of a refund, we craft it as follows. Notice that we pay back
   less than we initially deposited, leaving fees for the transaction to
   be confirmed.

   ::

       Refund layout:
           input:
               <customer script sig> 0 <redeem script>
           nLockTime: 1450302052
           output:
               dup hash160 <customer address> equalverify checksig [101,000 satoshis]

       Refund hex:
           010000000140185784207a4c3fe8c98fc0f7f85ac5774126307c76e36b1b735406f68aee81010000009c47304402203e08227a6db6517740afb9be61cdb7c40bbcd6e740b13e7aadc31c1c4d66b3c802204d6ae4e9f4e99456e1023685acdbe4d08faf5ca764d4abc8484ed8e625eacbe10101004c50632102d79987da792634d39f5c14741774311ab9421d2775c2bc9a608489de9277aa83ad670464da7156b175682103a5c2c5fe32a8ae5a8f67a314042cdd9eb33be822c6214d46109654ee269519faac0000000001888a0100000000001976a914206acc7cc7b959ec8d9466cddaaadf4a2fd1e7b088ac64da7156

   This causes the ``if`` statement in the redeem script to branch to
   the ``else`` section, where it will check the provided timestamp
   against the ``nLockTime`` field, and not require a merchant
   signature. A transaction of this style cannot be included in a block
   until the current time is after the ``nLockTime``.

3. **Customer sends deposit transaction and CLTV redeem script to
   merchant.** The merchant verifies that the redeem script is correctly
   formed, and that it requires a merchant signature. It validates the
   customer's deposit against the redeem script, and optionally waits
   until the deposit has been confirmed on the blockchain.

Channel payments
^^^^^^^^^^^^^^^^

1. **Customer creates a payment transaction and sends to merchant.**
   This transaction is similar to the refund transaction in that they
   both spend the same UTXO, however, we use a ``1`` to branch earlier
   in the ``if`` statement to require a merchant signature.

   ::

       Half-signed payment layout:
           input:
               <customer script sig> 1 <redeem script>
           nLockTime: 0
           outputs:
             - dup hash160 <merchant address> equalverify checksig [73,000 satoshis]
             - dup hash160 <customer address> equalverify checksig [28,000 satoshis]

       Half-signed payment hex:
           010000000140185784207a4c3fe8c98fc0f7f85ac5774126307c76e36b1b735406f68aee81010000009c483045022100f94e3073697be7138b00bf70e7ac60ba6dfcc2423df99d0f8b6f13966e1d3b7e022021bede7dd9fd09b6c72c3c51c70831df8c918cd4e4af175a59e511d5fc4eece601514c50632102d79987da792634d39f5c14741774311ab9421d2775c2bc9a608489de9277aa83ad670464da7156b175682103a5c2c5fe32a8ae5a8f67a314042cdd9eb33be822c6214d46109654ee269519faacffffffff02606d0000000000001976a9142a7a762597e0d97f8044a2eca976faa3af811eda88ac281d0100000000001976a914206acc7cc7b959ec8d9466cddaaadf4a2fd1e7b088ac00000000

2. **Merchant verifies and saves the transaction.**

Channel close
^^^^^^^^^^^^^

-  **Customer requests merchant to close the channel.** This happens if
   the customer spends the the full balance of the channel, or simply
   wishes to discontinue making payments in the channel. It is not a
   required part of the protocol, but it is generally courteous for the
   customer to do so. The merchant would then sign the remaining half of
   the transaction and broadcast it to the network.

   ::

       Fully-signed payment layout:
           input:
               <customer script sig> <merchant script sig> 1 <redeem script>
           nLockTime: 0
           outputs:
             - dup hash160 <merchant address> equalverify checksig [73,000 satoshis]
             - dup hash160 <customer address> equalverify checksig [28,000 satoshis]

       Fully-signed payment hex:
           010000000140185784207a4c3fe8c98fc0f7f85ac5774126307c76e36b1b735406f68aee8101000000e5483045022100f94e3073697be7138b00bf70e7ac60ba6dfcc2423df99d0f8b6f13966e1d3b7e022021bede7dd9fd09b6c72c3c51c70831df8c918cd4e4af175a59e511d5fc4eece601483045022100b26264031ddaf1104781e03893f6633669138be0050c813234be69fed81b9ff502203b93e0dfca7fa6a6f28041df8c56bcdb666be4b6e3494a84ce85d15bff104f2a01514c50632102d79987da792634d39f5c14741774311ab9421d2775c2bc9a608489de9277aa83ad670464da7156b175682103a5c2c5fe32a8ae5a8f67a314042cdd9eb33be822c6214d46109654ee269519faacffffffff02606d0000000000001976a9142a7a762597e0d97f8044a2eca976faa3af811eda88ac281d0100000000001976a914206acc7cc7b959ec8d9466cddaaadf4a2fd1e7b088ac00000000

*OR*

-  **Merchant closes the channel when it approaches the channel's
   expiration time.** The merchant has potentially received payment for
   goods/services, but will only lock those funds to their own address
   if they broadcast the last fully signed payment transaction before
   the channel expires. The channel's expiration time is dictated by the
   ``timestamp`` value in the CLTV-style transaction's redeem script.

*OR*

-  **Customer refunds its deposit after the expiration time has elapsed
   without any action by the merchant.** In this case, the customer
   already has a fully signed refund that it can broadcast, and does so
   without any requiring any interaction from the merchant.

Architecture
------------

Each payment channel is modeled by a state machine
``PaymentChannelStateMachine`` class,
which provides an interface to manipulating all of the client-side
channel state. This state is stored in a ``PaymentChannelModel``
object, which can be stored and restored to and from the channels
database. The ``PaymentChannelStateMachine`` class provides the
low-level transition functions on the channel state and is responsible
for creating and returning the underlying refund, deposit, and payment
transactions. It uses a ``WalletWrapper`` class
to sign transactions, but otherwise has no interaction with the outside
world.

The ``PaymentChannel`` class
provides an internal API (open, pay, sync, close, and properties) to a
payment channel, operates transitions on the state machine, and is the
the glue between state machine and the outside world -- the database,
the blockchain, and the payment channel server.

The ``PaymentChannelClient`` class
provides the top-level API for applications to ``open()``, ``pay()``,
``sync()``, ``status()``, ``close()``, and ``list()`` payment channels
by URL.

Finally, the ``channels`` cli is click-based cli implemented in.

The ``ChannelRequests`` class
takes in a wallet and creates a ``PaymentChannelClient`` in its
constructor. It uses the ``PaymentChannelClient`` and ``PaymentChannel``
APIs to lookup and operate payment channels, subject to an overridable
hard-coded policy (initial deposit amount = 100000, expiration time =
86400 seconds, and close out amount = 1000).

Developer Testing
-----------------

Use the following steps to get started using payment channels. **Please
note that having a confirmed, spendable bitcoin balance is a
prerequisite for the following.**

Setup
~~~~~

Fire up a barebones payment channel flask ``server.py``:

.. code:: python

    import flask
    from two1.wallet import Wallet
    from two1.bitserv.flask import Payment

    app = flask.Flask(__name__)
    payment = Payment(app, Wallet())

    @app.route('/current-temperature')
    @payment.required(50)
    def current_temperature():
        return 'Probably about 65 degrees Fahrenheit.'

    if __name__ == "__main__":
        app.run(host="0.0.0.0", port=5000, debug=True)

Set up a ``client.py`` to consume the server's REST API.

.. code:: python

    from two1.wallet import Wallet
    from two1.bitrequests import ChannelRequests

    requests = ChannelRequests(Wallet())

    response = requests.get("http://localhost:5000/current-temperature")
    print(response.text)

Start up the server:

.. code:: bash

    python3 server.py

In a new window, run the client:

.. code:: bash

    python3 client.py

Or you can simply buy at the command line:

.. code:: bash

    21 buy -p channel url http://localhost:5000/current-temperature

And use the ``channels`` CLI tool to check the status of your channels:

.. code:: bash

    channels list


``two1.channels``: module contents
=========================================
The ``two1.channels`` module is organized into the following submodules:

.. toctree::

   two1.channels.submodules
