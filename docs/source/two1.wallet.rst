The 21 Machine Wallet (``two1.wallet``)
===========================================
The wallet module within the 21 Bitcoin Library (``two1.wallet``)
provides a fully-functional HD wallet that integrates with 21
and is optimized for machine-to-machine
transactions. The wallet conforms to both `BIP-32
<https://github.com/bitcoin/bips/blob/master/bip-0032.mediawiki>`_ and
`BIP-44
<https://github.com/bitcoin/bips/blob/master/bip-0044.mediawiki>`_. It
can be accessed both via the command line and programmatically.

Quickstart
==========

Using ``two1.wallet`` via the ``wallet`` command line
---------------------------------------------------------

Command-line interaction with the wallet is provided via a `click
<http://click.pocoo.org/4/>`_ based CLI implemented in
:file:`two1/wallet/cli.py` which, after ``two1`` package
installation, is accessible as ``wallet``. 

A wallet can be created via the command-line::

  $ wallet create
  Wallet successfully created!
  Your wallet can be recovered using the following set of words (in that order).
  Please store them safely.

  home enter delay insect dose airport drink damp awake hedgehog cost dawn

Or, if a different location is desired::
  
  $ wallet -wp ~/test_wallets/test_wallet.json create
  Wallet successfully created!
  Your wallet can be recovered using the following set of words (in that order).
  Please store them safely.

  home enter delay insect dose airport drink damp awake hedgehog cost dawn

In either case, the mnemonic (set of words) given should be backed up
as it can be used to restore the wallet should there be any
corruption, disk loss, etc.


Using ``two1.wallet`` programmatically
------------------------------------------
To create a wallet programmatically, the easiest way is to use
``Two1Wallet.configure()``::

  from two1.blockchain.twentyone_provider import TwentyOneProvider
  from two1.wallet.two1_wallet import Two1Wallet

  options = dict(account_type="BIP32",
                 data_provider=TwentyOneProvider(),
		 passphrase="...",  # Can be empty or not provided
		 testnet=False)  # Or True if the wallet will be used with testnet

  configured =  Two1Wallet.configure(options)

``configured`` will be ``True`` if the wallet was created
successfully. If the wallet should be created in a location other than
the default, add ``wallet_path="..."`` to ``options``.

In the above snippet, a ``data_provider`` was required. The
``Two1Wallet`` class makes use of the data provider to get blockchain
information such as:

* Address balances
* Unspent transaction outputs (UTXOs) for addresses
* Transactions

It also uses the data provider to broadcast transactions to the
blockchain. The wallet is agnostic as to where it gets required data
as long as the data provider meets the API specification in
``two1.blockchain.base_provider``. This means you can write your
own provider should you want to use something other than the default
``TwentyOneProvider``.

The recommended way to interact with the created wallet is to make use
of ``two1.wallet.two1_wallet.Wallet`` 
to initiate a ``Two1Wallet`` object. A very
simple example to get the wallet's current payout address is::

  from two1.wallet.two1_wallet import Wallet

  w = Wallet()

  print("payout address: %s" % w.get_payout_address())

It also assumes that the caller wants the currently
logged-in user's default wallet (found in
:file:`~/.two1/wallet/default_wallet.json`). Should the path to the
desired wallet be different than this, the ``wallet_path`` argument
can be provided::

  from two1.wallet.two1_wallet import Wallet

  w = Wallet(wallet_path=...)

  print("payout address: %s" % w.get_payout_address())


``two1.wallet``: module contents
====================================
The ``two1.wallet`` module is organized into the following submodules:
   
.. toctree::

   two1.wallet.submodules
