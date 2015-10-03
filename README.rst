``two1``: buy/sell anything on the internet with Bitcoin.
=========================================================
``two1`` is a command line tool and library that allows users to mine
Bitcoin, use it to buy and sell API calls, set up world-readable
machine-payable endpoints, and publish them to the Many Machine Market
from any Unix command line.

Running Tests
=============
We use `nose <https://nose.readthedocs.org/en/latest/>`_ as our
primary tool for discovering and running tests. Run the following
command to execute the test suite:

.. code-block:: bash
   $ nosetests -v --with-doctest

Most tests will fail at this point. You can also run just a subset of
tests as follows by specifying a file or directory as input:

.. code-block:: bash
   $ nosetests -v two1/bitcoin/tests

Read the `nose documentation
<http://nose.readthedocs.org/en/latest/testing.html>`_ and `TDD in
Python <http://bit.ly/tdd-python-book>`_ for more.

Developer Installation
======================
The ``two1`` app is built on the `click <http://click.pocoo.org>`_
command line framework and uses `setuptools
<https://github.com/pypa/sampleproject>`_ and `virtualenv
<http://click.pocoo.org/4/quickstart/#virtualenv>`_ to build a
reproducible ``two1`` app environment suitable for `pip-based
distribution
<https://packaging.python.org/en/latest/distributing.html>`_.

Here's how to install the command line app for development purposes:

.. code-block:: bash

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
   $ two1 --help

If you follow these steps, you will have the ``two1`` command line app
in your path in an uninstallable way, and will also be able to edit
the files in the ``two1`` directory and see those changes reflected in
the command line app in realtime.

Developer Environment Variables
===============================
The following set of environment variables are useful for development purposes:

- TWO1_DEV 
This sets the debug mode on. This will automatically use `http://127.0.0.1:8000` as the hostname for the 21-API server.

.. code-block:: bash

   $ export TWO1_DEV=1

- TWO1_DEV_HOST 
This sets a custom 21-API host to which the CLI will make requests.

.. code-block:: bash

   $ export TWO1_DEV_HOST=localhost:5000

The Codebase
============

The root directory
------------------
The top level contains the following files:

 - `<Dockerfile>`_: Instructions to Dockerize ``two1.bitcoin``
 - `<Procfile>`_:  Deploy ``two1.examples`` to Heroku
 - `<README.rst>`_: This documentation file
 - `<setup.cfg>`_: Configuration for setup.py
 - `<setup.py>`_: The build script for pip/setup.py install of ``two1``
 - `<requirements.txt>`_: The pip dependencies
 - `<runtime.txt>`_: File needed for Heroku deployment (`see here <https://devcenter.heroku.com/articles/python-runtimes/>`_)

And the following subdirectories:

 - `<docs>`_: Documentation directory, including semi-automatically generated sphinx documentation from .rst docstrings
 - `<setup>`_: Setup files for running on jenkins and rpi. TODO: move ``jenkins``/ ``rpi`` into ``tests``/ ``bin`` respectively.
 - `<tests>`_: Tests for the overall ``two1`` codebase
 - `<two1>`_: The primary codebase directory

The ``two1`` directory
----------------------
Going down one level within the ``two1`` subdirectory, we see the
following files:

 - `cli.py <two1/cli.py>`_: The main entry point for the ``two1`` command-line interface
 - `config.py <two1/config.py>`_: Manages configuration variables for the ``two1`` CLI
 - `debug.py <two1/debug.py>`_: Simple debugging routines for ``two1`` CLI
 - `uxstring.py <two1/uxstring.py>`_: Strings for the ``two1`` CLI user interface

And the following subdirectories:

 - `bitcoin <two1/bitcoin>`_: Core bitcoin utilities for handling blocks, script, et al.
 - `bitcurl <two1/bitcurl>`_: Standalone bitcurl utility. TODO: fold this into buy.py and then deprecate.
 - `commands <two1/commands>`_: The client commands exposed by ``two1``
 - `crypto <two1/crypto>`_: Pure Python implementation of Bitcoin's ECDSA (Elliptic Curve Digital Signature Algorithm)
 - `djangobitcoin <two1/djangobitcoin>`_: Django implementation of 402 endpoints
 - `gen <two1/gen>`_: Generated code for Google Protocol Buffers
 - `lib <two1/lib>`_: Libraries used by the ``two1`` client for communicating with server and authenticating
 - `mining <two1/mining>`_: Core bitcoin utilities for mining both on CPUs and as part of a pool.
 - `wallet <two1/wallet>`_: The Python bitcoin wallets.

The ``two1/commands`` subdirectory
----------------------------------
Descending yet one more level within ``/two1/commands``, we have the
core of the program. These are the commands that clients use to mine
Bitcoin and buy and sell on the Many Machine Market (MMM). They are:

 - `mine.py <two1/commands/mine.py>`_: Mine Bitcoin locally via a CPU or built-in mining chip
 - `search.py <two1/commands/search.py>`_: Find machine-payable endpoints on the MMM
 - `buy.py <two1/commands/buy.py>`_: Buy from a machine-payable endpoint
 - `rate.py <two1/commands/rate.py>`_: Rate the seller of a machine-payable endpoint
 - `sell.py <two1/commands/sell.py>`_: Launch a machine-payable endpoint on the current machine
 - `publish.py <two1/commands/publish.py>`_: Publish that machine-payable endpoint to the MMM
 - `status.py <two1/commands/status.py>`_: View the status of mining and machine-payable purchases

The ``two1/bitcoin`` subdirectory
----------------------------------

 - `block.py <two1/bitcoin/block.py>`_: Bitcoin Block header calculation and Merkle tree API
 - `crypto.py <two1/bitcoin/crypto.py>`_: Generate private keys, sign messages, serialize/deserialize data
 - `exceptions.py <two1/bitcoin/exceptions.py>`_: Exceptions thrown in bitcoin-related code
 - `hash.py <two1/bitcoin/hash.py>`_: Assist with ordering hashes properly for consumption by block.py
 - `script.py <two1/bitcoin/script.py>`_: Parse scripts and assemble/disassemble.
 - `txn.py <two1/bitcoin/txn.py>`_: Represent transactions: input, output, and coinbases.
 - `utils.py <two1/bitcoin/utils.py>`_: Utility functions, mostly related to serializing and difficulty

The ``two1/mining`` subdirectory
----------------------------------

 - `async_exception_handler.py <two1/mining/async_exception_handler.py>`_: Self-explanatory. Used by asyncio to handle exceptions.
 - `client.py <two1/mining/client.py>`_: Mining client that communicates with the pool.
 - `client_message_handler.py <two1/mining/client_message_handler.py>`_: Encode and send to server. Receive and parse messages from server.
 - `client_task_factory.py <two1/mining/client_task_factory.py>`_: Stub code to initiate tasks from client
 - `coinbase.py <two1/mining/coinbase.py>`_: Builds the coinbase transaction
 - `configs.py <two1/mining/configs.py>`_: Loads mining-related configuration information
 - `cpu_miner.py <two1/mining/cpu_miner.py>`_: CPU-based miner
 - `message_factory.py <two1/mining/message_factory.py>`_: Protobuf and Laminar message factory classes

This completes the guided tour.
