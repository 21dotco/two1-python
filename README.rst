``two1``: buy/sell anything on the internet with Bitcoin.
=============================================================
``two1`` is a command line tool that allows users to get and mine Bitcoin, use
BTC to buy API calls, set up world-readable machine-payable endpoints,
publish them to the `Many Machine Market <http://mmm.21.co>`_, and fully
participate in this grand experiment in decentralization we call Bitcoin.

It can also be used as a Python library:

.. code-block:: python

    >>> from two1.commands.get import get
    >>> bitcoin = get()
    >>> bitcoin.balance()
    "15000 Satoshis over 1 address(es) in 1 wallet(s)"
    >>> result = two.buy(endpoint='http://mmm.21.co/text2speech-mp3', 
                         stdin="Hello World", 
                         bitin=bitcoin)
    >>> result.stdout, result.stderr, result.bitout                                        ...     

While ``two1`` can be used as a standalone app for users who bring their own
Bitcoin and 402-capable web server, it is meant to work with a `21 Bitcoin
Node <http://www.21.co/>`_. For full instructions on how to use the
application, please see below.


``two1``: developer installation
================================
The ``two1`` app is built on the `click <http://click.pocoo.org>`_ command
line framework and uses `setuptools
<https://github.com/pypa/sampleproject>`_ and `virtualenv
<click.pocoo.org/4/quickstart/#virtualenv>`_ to build a reproducible
``two1`` app environment suitable for `pip-based distribution
<https://packaging.python.org/en/latest/distributing.html>`_.

Here's how to install the command line app for development purposes:

.. code-block:: bash

   # Install homebrew and Python3
   $ ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
   $ brew install python3

   # Download the repo, setup a virtual environment and install requirements
   $ git clone git@github.com:21dotco/two1.git
   $ cd two1
   $ pyvenv venv
   $ source venv/bin/activate
   $ pip3 install --upgrade pip
   $ pip3 install -r requirements.txt

   # By using the --editable flag, pip symbolically links an egg file
   # You can then edit locally and rerun ``two1`` to see changes.
   # http://click.pocoo.org/4/setuptools/#setuptools-integration
   # https://pip.pypa.io/en/latest/reference/pip_install.html#editable-installs
   $ pip3 install --editable .
   $ two1 --help

If you follow these steps, you will have the ``two1`` command line app in
your path in an uninstallable way, and will also be able to edit the files
in the ``two1`` directory and see those changes reflected in the command
line app in realtime.
