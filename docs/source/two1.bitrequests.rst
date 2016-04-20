The 21 BitRequests Library
==========================

Overview
--------

BitRequests wraps the python HTTP
`Requests <http://docs.python-requests.org/en/latest/>`__ library,
adding a simple API for users to pay for resources. It enables a client
(also referred to as a customer) to pay a server (also referred to as a
merchant) for a resource.

.. figure:: https://assets.21.co/two1docs/bitrequests.png
   :alt: 402 flow

The 402 payment-resource exchange adds an intermediary negotiation step
between a standard HTTP request/response session. The following is how
the transaction would occur for a ``GET`` request.

1. **GET /resource** - a client asks the server for some data resource
   (part of the standard HTTP request/response architecture).
2. **402 PAYMENT REQUIRED** - the server responds with HTTP status code
   `402 <https://www.w3.org/Protocols/rfc2616/rfc2616-sec10.html>`__ to
   inform the client that the resource cannot be accessed without
   payment. The server includes headers to instruct payment.
3. **GET /resource (with proof of payment)** - the client repeats its
   initial request with a header that advises the server how payment is
   being made.
4. **200 OK** - the server responds to the client with the requested
   data (part of the standard HTTP request/response architecture).

Steps ``1`` and ``4`` are fairly well-understood in the world of REST
APIs. Instead, this document focuses on the interaction that occurs
between client and server in steps ``2`` and ``3``, which is the core
innovation of the HTTP 402 protocol.

402 PAYMENT REQUIRED
--------------------

As of current, a merchant server's initial response will be
``HTTP/1.0 402 PAYMENT REQUIRED`` with the addition of a number of
payment headers. This response informs the client how purchase should be
made to retrieve the resource.

Each header and its related payment method is discussed in more detail
in their respective sections within **Paid GET** below.

**Price** - the amount (in
`satoshis <https://en.bitcoin.it/wiki/Satoshi_%28unit%29>`__) that is
required to be paid for the resource

::

    Price: 3500

**Bitcoin-Address** - the bitcoin address where an ``onchain`` payment
should be made

::

    Bitcoin-Address: 19tQ4iBbdhZsQKgZoeY3gVM1yyhGPxkiPM

**Username** - the server's username in an ``offchain`` payments network

::

    Username: HelloNakaMoto

**Bitcoin-Payment-Channel-Server** - the server URL where payment
``channels`` activity should occur

::

    Bitcoin-Payment-Channel-Server: http://example-merchant-server.com/payment

Paid GET
--------

In the client's new request, it needs to provide some indication that
payment can or will be made. Let's take a look at how that works for the
currently supported payment methods: ``onchain``, ``offchain``, and
``channels``.

On-Chain Bitcoin Method
^^^^^^^^^^^^^^^^^^^^^^^

In this case, the server has recently sent a 402 response with headers
to the client

::

    Price: 1000
    Bitcoin-Address: 19tQ4iBbdhZsQKgZoeY3gVM1yyhGPxkiPM

In order to provide proof of the payment, the client builds a signed
transaction that pays to that address in the amount requested. The
client then sends the raw, serialized transaction to the server in a
header, along with a recommended return address

::

    Bitcoin-Transaction: 0100000002b443358253dcd55b2f0761b58e44584f0c18670b9dd0f0ba6b96e092a26d4e93000000006b483045022100abb81fed203e79900b8f173e35e6eabd43e77e3c711fe6dd55c14b17bc8dc81b022001694074a820eec9925baccf264f82fc64c2b0e54674a45ddf8fe145d64fd0fe012102a9f537eadeee9384d5d42c90d20376f0e171fbba43b8a6726eb35d7bb7c11255ffffffff51f518e0d5694d53fa7c5d5e0396c4f5b8f1ee5b5cbc0f0f0e380ad5e547c644000000006a47304402202b836f0038234809bf8e9f1945f7cd615ae56ef3cf22a2be463620a3dddff254022007d70d6e7329973a422893b373eecc7881cb7ae4bd8a6ddfc160b0843ecc42ce012102a9f537eadeee9384d5d42c90d20376f0e171fbba43b8a6726eb35d7bb7c11255ffffffff02e8030000000000001976a914617979206c6d616f20202020202020202020202088acc8190000000000001976a914f6955d9fb2ccca7de9e4d1fd3a9509e2a10234d688ac00000000
    Return-Wallet-Address: 1PUpAJXz8T6G7yTFW4rdvepKhcRcy8wwMg

Off-Chain Bit-Transfer Method
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If a server responds with a ``Username``, a client can make transactions
on the 21 network, avoiding the need to wait for transaction
confirmation on the blockchain.

::

    Price: 1000
    Username: HelloNakaMoto

In order to provide proof of the payment, the client builds and sends a
bit-transfer token, which the server can use to redeem payment on the 21
network. The bit-transfer token is a serialized JSON object that
contains keys for ``payer``, ``payee_username``, ``amount``,
``timestamp``, and ``description``. The client then includes that token
encoded as a UTF-8 string, and also includes a signed copy of the token
using their machine wallet private key.

::

    Bitcoin-Transfer: {"payee_username": "HelloNakaMoto", "description": "http://example-merchant-server.com/resource", "payer": "Bitcoiner11", "amount": 1000, "payee_address": "19tQ4iBbdhZsQKgZoeY3gVM1yyhGPxkiPM", "timestamp": 1453338704.678601}
    Authorization: 1o8J+ECKu3TtLfbTYbCfSljwFnb3wup9/BUZk8NE2bp5jNPLrU9umbovWUqlEkPFx0ATQEvmvLa1H4dju2XXog==

Payment Channel Method
^^^^^^^^^^^^^^^^^^^^^^

Conversely, if a server responds with a
``Bitcoin-Payment-Channel-Server`` header, a client can use that URI to
negotiate an out-of-band payment channel.

::

    Price: 1000
    Bitcoin-Payment-Channel-Server: http://example-merchant-server.com/payment

The client then uses that payment channel server to open a channel and
make a payment in the required amount. The client receives a payment
transaction id that it can use to redeem the payment with the server at
the original endpoint.

::

    Bitcoin-Payment-Channel-Token: f39d9402cef5292a14c9ba1722cb2c99fafe082505bd2d830b68beeb87b8237a

Important Notes
---------------

Safety and Idempotence
^^^^^^^^^^^^^^^^^^^^^^

You should notice that the examples so far have used ``GET`` as the
primary HTTP method for interacting with a server. ``GET`` is safe
insofar as it is being used for its intended purpose of information
retrieval. In other words, repeated ``GET`` requests should result in
the same response, without side-effects.

Requiring payment for a non-idempotent method like ``POST`` can be
peculiar, and special care should be taken to ensure that side-effects
do not ripple through your application.

For example, say a client wishes to "price out" your endpoint by sending
a ``POST`` request with data such that they can receive a ``402``
response with the cost of the endpoint. Surprise! The endpoint was free,
and their request (whether or intentionally or not) is processed.

Handling Errors
^^^^^^^^^^^^^^^

Traditionally, if a server encounters an error, due to its own fault or
the fault of the client, it can simply respond with a standard ``4xx``
or ``5xx`` status code. In the case of a server who accepts payment,
that server has the delicate task of handling errors ever so gracefully.

A client who sends payment, but does not provide adequate parameters to
the API, should perhaps not be charged. That is, the server should
validate parameters **prior** to accepting payment, else deal with a
provided return address and reverse the payment.

There is certainly also the possibility that a server crashes for
whatever reason, and does not honor its end of the 402 exchange by
providing the requested service after accepting payment. Some method for
recompensating the client should be put in place for these types of
circumstances.

BitRequests Class
-----------------

Definition
~~~~~~~~~~

**BitRequests** is an abstract base class which provides much the client
functionality of the 402 payment-resource exchange. It offers the
following API:

**request()**

1. Make the initial request
2. Catch the 402 response
3. Run the implemented ``make_402_payment()`` method, which returns
   proof of payment headers
4. Repeat the initial request with payment headers appended
5. Return the requested data

Convenience wrappers around ``request()`` to make a HTTP requests

-  **get()**
-  **post()**
-  **put()**
-  **delete()**
-  **head()**

**BitTransferRequests**, **OnChainRequests**, and **ChannelRequests**
implement the ``BitRequests`` interface and define the primary payment
function.

**make\_402\_payment()** - Contains all the logic for making a payment
of the desired method. It should return headers that a merchant server
can use to process payment.

**get\_402\_info()** - A function for returning only the 402 payment
headers for a resource.

**init** - The class constructor should accept objects necessary to
create payments. In the case of the three implementations listed above,
the primary payment-creation object is a ``two1.wallet.Wallet`` object.

Usage
~~~~~

The API for using payment methods has aimed to be as consistent as
possible. This should ideally allow users to seamlessly switch between
payment methods without too much extra configuration.

::

    # BitTransferRequests
    from two1.commands.util import config
    from two1.wallet import Wallet
    from two1.bitrequests import BitTransferRequests
    requests = BitTransferRequests(Wallet(), config.Config().username)
    requests.get('http://localhost:5000/my-test-endpoint').text

    # OnChainRequests
    from two1.wallet import Wallet
    from two1.bitrequests import OnChainRequests
    requests = OnChainRequests(Wallet())
    requests.get('http://localhost:5000/my-test-endpoint').text

    # ChannelRequests
    from two1.wallet import Wallet
    from two1.bitrequests import ChannelRequests
    requests = ChannelRequests(Wallet())
    requests.get('http://localhost:5000/my-test-endpoint').text


``two1.bitrequests``: module contents
=========================================
The ``two1.bitrequests`` module is organized into the following submodules:

.. toctree::

   two1.bitrequests.submodules
