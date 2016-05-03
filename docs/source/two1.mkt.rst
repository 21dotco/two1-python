Two1 Marketplace
================

The ``two1.mkt`` module provides a convenient wrapper for interacting
with the 21.co marketplace.

Basic Usage
~~~~~~~~~~~

.. code:: python

    from two1 import mkt

    zipdata = mkt.zipdata.collect(zip_code=94109)

    print("information about {}:".format(zipdata["Zipcode"]))
    print("  location:    {}, {}".format(zipdata["City"], zipdata["State"]))
    print("  population:  {}".format(zipdata["EstimatedPopulation"]))
    print("  coordinates: ({}, {})".format(zipdata["Lat"], zipdata["Long"]))

Overview
~~~~~~~~

The ``two1.mkt`` module handles the following steps for users, and makes
assumptions about default configuration along the way.

1. Marketplace discovery
2. Instantiation of ``Wallet`` and ``Bitrequests`` objects
3. Sending data to the server
4. Handling server response

Creating Requests
~~~~~~~~~~~~~~~~~

To use ``mkt`` we need to find a host and issue a request for some
resource. The following code won't work yet, but takes us a few steps
forward.

.. code:: python

    from two1 import mkt

    mkt.zipdata.collect

What's happening:

1. Importing ``mkt`` implicitly instantiates a new Market object
2. The default host is set to ``https://mkt.21.co``
3. The lookup of attribute ``zipdata.collect`` sets the request URI to
   ``https://mkt.21.co/zipdata/collect``

Next, we need to define how we will query data to that URI.

Sending Data
~~~~~~~~~~~~

A marketplace endpoint will only accept data via ``GET`` or ``POST``
request. Without spending extra roundtrips, we need a way to distinguish
between these two HTTP methods.

Since ``GET`` requests accept data as simple key-value pairs, we also
represent them as such using function keyword arguments:

.. code:: python

    mkt.zipdata.collect(zip_code=94109)

This is functionally equivalent to buying the marketplace API
``https://mkt.21.co/zipdata/collect?zip_code=94109``.

On the other hand, ``POST`` requests can send more complex data, and is
more aptly represented in JSON format:

.. code:: python

    mkt.extract_title.url({"url": "https://21.co"})

This is functionally eqiuvalent to buying the marketplace API
``https://mkt.21.co/extract_title/url`` with
``"{\"url\": \"https://21.co\"}"`` serialized in the body (and a header
``Content-Type: application/json``)

So how do we know when to use one syntax versus another? You'll need to
be familiar with the API that you're purchasing and know how it expects
to receive data. Until further changes are made to the underlying 402
protocol, we can't reliably predict what request type that and API
supports in advance.


``two1.mkt``: module contents
===================================
The ``two1.mkt`` module is organized into the following submodules:

.. toctree::

    two1.mkt.submodules
