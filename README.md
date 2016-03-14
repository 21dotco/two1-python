<!--- Do not edit this file directly!
This file was dynamically generated from README.md.template.
Edit that and then run python3 generate_readme.py -->

# `two1`: buy/sell anything on the internet with Bitcoin.

`two1` is a command line tool and library that allows users to mine
Bitcoin, use it to buy and sell API calls, set up world-readable
machine-payable endpoints, and publish them to the Many Machine Market
from any Unix command line.

# Developer Installation

Here's how to install the command line app for development purposes:

```bash
# Install homebrew and Python3
$ ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
$ brew install python3

# Download repo, set up virtualenv,  install requirements
$ git clone git@github.com:21dotco/two1.git
$ cd two1
$ pyvenv venv
$ source venv/bin/activate
$ pip3 install --upgrade pip
$ pip3 install -r requirements.txt

# By using the --editable flag, pip symbolically links an egg file
# You can then edit locally and rerun ``two1`` to see changes.
# http://click.pocoo.org/4/setuptools/#setuptools-integration
# pip.pypa.io/en/latest/reference/pip_install.html#editable-installs
$ pip3 install --editable .

# Start the walletd daemon
$ walletd

# Verify installation and create wallet
$ two1 --help
$ two1 status
```

If you follow these steps, you will have the ``two1`` command line app in your
path, and will also be able to edit the files in the ``two1`` directory and see
those changes reflected in the command line app in realtime.

# Running Tests

Unit tests can be run with `pytest <http://pytest.org/latest/>`_:

```bash
$ py.test
```

# The Codebase
## The `two1` directory
 - [__init__.py](two1/__init__.py): Two1 project variables.
 - [cli.py](two1/cli.py): The 21 command line interface.

## The `two1/commands` directory
 - [buy.py](two1/commands/buy.py): Buy from a machine-payable endpoint.
 - [doctor.py](two1/commands/doctor.py): When you are not feeling well come see the Doctor
 - [mine.py](two1/commands/mine.py): Mine Bitcoin locally via a CPU or built-in mining chip
 - [sell.py](two1/commands/sell.py): Launch a machine-payable endpoint on the current machine
 - [status.py](two1/commands/status.py): View the status of mining and machine-payable purchases

## The `two1/commands/helpers` directory
 - [sell_helpers.py](two1/commands/helpers/sell_helpers.py): Helper methods for the 21 sell command.

## The `two1/commands/util` directory
 - [account.py](two1/commands/util/account.py): Utility functions for user accounts.
 - [bitcoin_computer.py](two1/commands/util/bitcoin_computer.py): Contains methods to interact with the bitcoin computer hardware
 - [config.py](two1/commands/util/config.py): Manages configuration variables for the two1 CLI.
 - [uxstring.py](two1/commands/util/uxstring.py): Strings for the two1 CLI user interface
 - [wallet.py](two1/commands/util/wallet.py): Utility functions for user wallets.
 - [zerotier.py](two1/commands/util/zerotier.py): Simple wrapper for zerotier-cli

## The `two1/lib/bitcoin` directory
 - [__init__.py](two1/lib/bitcoin/__init__.py): The bitcoin module within the 21 Bitcoin Library (``two1.lib.bitcoin``) provides
 - [block.py](two1/lib/bitcoin/block.py): This submodule provides the MerkleNode, Block, BlockHeader, and CompactBlock
 - [crypto.py](two1/lib/bitcoin/crypto.py): This submodule provides the PublicKey, PrivateKey, and Signature classes.
 - [exceptions.py](two1/lib/bitcoin/exceptions.py): This is a simple submodule that enumerates the different kinds of exceptions
 - [hash.py](two1/lib/bitcoin/hash.py): this submodule provides a Hash class for interacting with SHA-256 hashes
 - [script.py](two1/lib/bitcoin/script.py): This submodule provides a single Script class that has knowledge of all
 - [script_interpreter.py](two1/lib/bitcoin/script_interpreter.py): This submodule provides a single ScriptInterpreter class to be used in
 - [txn.py](two1/lib/bitcoin/txn.py): This submodule provides Transaction, Coinbase, TransactionInput,
 - [utils.py](two1/lib/bitcoin/utils.py): This submodule provides functions for accomplishing common tasks encountered

## The `two1/lib/bitrequests` directory
 - [__init__.py](two1/lib/bitrequests/__init__.py): BitRequests wraps the python Requests library, adding a simple API for users
 - [bitrequests.py](two1/lib/bitrequests/bitrequests.py): This module provides various BitRequests methods, including:

## The `two1/lib/bitserv` directory
 - [__init__.py](two1/lib/bitserv/__init__.py): The BitServ library adds a simple API for servers to create payable
 - [models.py](two1/lib/bitserv/models.py): This module provides data management for payment servers.
 - [payment_methods.py](two1/lib/bitserv/payment_methods.py): This module contains methods for making paid HTTP requests to 402-enabled servers.
 - [payment_server.py](two1/lib/bitserv/payment_server.py): This module implements the server side of payment channels.
 - [wallet.py](two1/lib/bitserv/wallet.py): Wrapper around the two1 wallet for payment channels.

## The `two1/lib/bitserv/django` directory
 - [__init__.py](two1/lib/bitserv/django/__init__.py): Bitserv implementation for Django.
 - [decorator.py](two1/lib/bitserv/django/decorator.py): Django bitserv payment library for selling 402 API endpoints.
 - [models.py](two1/lib/bitserv/django/models.py): Payment models for a bitserv server.
 - [urls.py](two1/lib/bitserv/django/urls.py): Added URLs for a bitserv server.
 - [views.py](two1/lib/bitserv/django/views.py): Added views for a bitserv server.

## The `two1/lib/bitserv/flask` directory
 - [__init__.py](two1/lib/bitserv/flask/__init__.py): Bitserv implementation for Flask.
 - [decorator.py](two1/lib/bitserv/flask/decorator.py): Flask bitserv payment library for selling 402 API endpoints.

## The `two1/lib/bitserv/tests` directory
 - [test_channels.py](two1/lib/bitserv/tests/test_channels.py): Tests for payment channel functionality.

## The `two1/lib/blockchain` directory
 - [__init__.py](two1/lib/blockchain/__init__.py): The blockchain module within the 21 Blockchain Library allows you to receive
 - [base_provider.py](two1/lib/blockchain/base_provider.py): This submodule provides an abstract base class for a Provider, which
 - [block_cypher_provider.py](two1/lib/blockchain/block_cypher_provider.py): This submodule provides a concrete `BlockCypherProvider` class that provides
 - [exceptions.py](two1/lib/blockchain/exceptions.py): This is a simple submodule that enumerates the different kinds of exceptions
 - [insight_provider.py](two1/lib/blockchain/insight_provider.py): This submodule provides a concrete `InsightProvider` class that provides
 - [mock_provider.py](two1/lib/blockchain/mock_provider.py): This submodule provides a concrete `MockProvider` class that provides
 - [twentyone_provider.py](two1/lib/blockchain/twentyone_provider.py): This submodule provides a concrete `TwentyOneProvider` class that provides

## The `two1/lib/channels` directory
 - [__init__.py](two1/lib/channels/__init__.py): The payment channel protocol allows for fast, high-volume payments to occur
 - [blockchain.py](two1/lib/channels/blockchain.py): Wraps various blockchain data sources to provide convenience methods for
 - [cli.py](two1/lib/channels/cli.py): Command-line interface for managing client-side payment channel management.
 - [database.py](two1/lib/channels/database.py): Provides persistent storage and retrieval of payment channel state.
 - [paymentchannel.py](two1/lib/channels/paymentchannel.py): Provides and object to represent and manage a payment channel.
 - [paymentchannelclient.py](two1/lib/channels/paymentchannelclient.py): A high-level client that can open, close, and pay across many channels.
 - [server.py](two1/lib/channels/server.py): Interfaces with a payment channel server over `http` and `mock` protocols.
 - [statemachine.py](two1/lib/channels/statemachine.py): Manages state transitions for PaymentChannel objects.
 - [walletwrapper.py](two1/lib/channels/walletwrapper.py): Wraps the Two1 `Wallet` to provide methods for payment channel management.

## The `two1/lib/mining` directory
 - [client.py](two1/lib/mining/client.py): Mining client that communicates with the pool.
 - [client_message_handler.py](two1/lib/mining/client_message_handler.py): Encode and send to server. Receive and parse messages from server.
 - [coinbase.py](two1/lib/mining/coinbase.py): Builds the coinbase transaction
 - [cpu_miner.py](two1/lib/mining/cpu_miner.py): CPU-based miner

## The `two1/lib/server` directory
 - [analytics.py](two1/lib/server/analytics.py): Handles usage and error statistics and communication
 - [login.py](two1/lib/server/login.py): Handles client-side user account setup and authentication.
 - [machine_auth.py](two1/lib/server/machine_auth.py): Uses a PrivateKey to provide signing capabilities for authentication.
 - [machine_auth_wallet.py](two1/lib/server/machine_auth_wallet.py): Wraps a Wallet object and adds signing capabilities for authentication.
 - [message_factory.py](two1/lib/server/message_factory.py): Generates new swirl messages.

## The `two1/tests` directory
 - [mock.py](two1/tests/mock.py): Mock objects for testing.

## The `two1/tests/commands` directory
 - [test_buy.py](two1/tests/commands/test_buy.py): Unit tests for `21 buy`.
 - [test_doctor.py](two1/tests/commands/test_doctor.py): Doctor command unit tests
 - [test_flush.py](two1/tests/commands/test_flush.py): Flush command unit tests.
 - [test_send.py](two1/tests/commands/test_send.py): Unit tests for `21 send`.

## The `two1/tests/commands/util` directory
 - [test_config.py](two1/tests/commands/util/test_config.py): Unit tests for `21 config`.
 - [test_zerotier.py](two1/tests/commands/util/test_zerotier.py): Unit tests for the zerotier utility

## The `two1/lib/util` directory
 - [uxstring.py](two1/lib/util/uxstring.py): Strings for the two1 CLI user interface
 - [zerotier.py](two1/lib/util/zerotier.py): Simple wrapper for zerotier-cli

