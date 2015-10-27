two1.lib.wallet package
=======================

The wallet package provides a fully-functional, programatic HD wallet that conforms to both
`BIP-32 <https://github.com/bitcoin/bips/blob/master/bip-0032.mediawiki>`_ and
`BIP-44 <https://github.com/bitcoin/bips/blob/master/bip-0044.mediawiki>`_.

===================
Command-line access
===================

Command-line interaction is also provided via a `click <http://click.pocoo.org/4/>`_ based CLI implemented in :file:`two1/lib/wallet/cli.py` which, after ``two1`` package installation, is accessible as ``wallet``. A multi-threaded JSON-RPC daemon is also implemented in :file:`two1/lib/wallet/daemon.py` to provide faster access for repeated calls. The daemon removes the overhead of account discovery, transaction downloads, balance updates, etc.

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

In either case, the mnemonic (set of words) given should be backed up as it can be used to restore the wallet should there be any corruption, disk loss, etc.

Similarly, the wallet daemon can be started and stopped as follows::

  $ wallet startdaemon
  walletd successfully started.
  $ wallet stopdaemon
  walletd successfully stopped.

The first call to ``wallet startdaemon`` will also install scripts to automatically launch the daemon upon subsequent user logins (only for Mac OS X and newer Linux distributions that use ``systemd`` as their init system). Should you not want to have it be launched automatically, it can be manually started::

  $ walletd --help
  Usage: walletd [OPTIONS]
  
    Two1 Wallet daemon
  
  Options:
    -wp, --wallet-path PATH         Path to wallet file  [default: /Users/nigel/
                                    .two1/wallet/default_wallet.json]
    -b, --blockchain-data-provider [twentyone|chain]
                                    Blockchain data provider service to use
                                    [default: twentyone]
    -ck, --chain-api-key-id STRING  Chain API Key (only if -b chain)
    -cs, --chain-api-key-secret STRING
                                    Chain API Secret (only if -b chain)
    -u, --data-update-interval INTEGER RANGE
                                    How often to update wallet data (seconds)
                                    [default: 25]
    -d, --debug                     Sets the logging level to debug
    --version                       Show the version and exit.
    -h, --help                      Show this message and exit.

==================
Programatic access
==================

To create a wallet programatically, the easiest way is to use ``Two1Wallet.configure()``::

  from two1.lib.blockchain.twentyone_provider import TwentyOneProvider
  from two1.lib.wallet.two1_wallet import Two1Wallet

  options = dict(account_type="BIP32",
                 data_provider=TwentyOneProvider(),
		 passphrase="...",  # Can be empty or not provided
		 testnet=False)  # Or True if the wallet will be used with testnet

  configured =  Two1Wallet.configure(options)

``configured`` will be ``True`` if the wallet was created successfully. If the wallet should be created in a location other than the default, add ``wallet_path="..."`` to ``options``.

In the above snippet, a ``data_provider`` was required. The ``Two1Wallet`` class makes use of the data provider to get blockchain information such as:

* Address balances
* Unspent transaction outputs (UTXOs) for addresses
* Transactions

It also uses the data provider to broadcast transactions to the blockchain. The wallet is agnostic as to where it gets required data as long as the data provider meets the API specification in ``two1.lib.blockchain.base_provider``. This means you can write your own provider should you want to use something other than the default ``TwentyOneProvider``.

The recommended way to interact with the created wallet is to make use of ``two1.lib.wallet.two1_wallet.Wallet`` which abstracts daemon vs object usage. If a daemon is found running on the system, a ``Wallet`` instance will connect to it and use it. If not, the ``Wallet`` instance will instead instantiate a ``Two1Wallet`` object. A very simple example to get the wallet's current payout address is::

  from two1.lib.wallet.two1_wallet import Wallet

  w = Wallet()

  print("payout address: %s" % w.get_payout_address())

This code snippet will automatically search for a daemon and connect to it if found. It also assumes that the caller wants the currently logged-in user's default wallet (found in :file:`~/.two1/wallet/default_wallet.json`). Should the path to the desired wallet be different than this, the ``wallet_path`` argument can be provided::

  from two1.lib.wallet.two1_wallet import Wallet

  w = Wallet(wallet_path=...)

  print("payout address: %s" % w.get_payout_address())

In this case, if there is a daemon running, the ``Wallet`` object will ensure that the daemon has been started with the correct ``wallet_path``. If the daemon is serving a different wallet, the ``Wallet`` object will revert to instantiating a ``Two1Wallet`` object for the desired wallet and operate directly on that object.


Submodules
----------

.. toctree::

    two1.lib.wallet.submodules
