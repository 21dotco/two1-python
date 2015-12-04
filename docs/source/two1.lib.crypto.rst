two1.lib.crypto package
====================

The crypto package provides an interface to the low-level
cryptographic functions used in Bitcoin to create public keys and
signatures using the Elliptic Curve Digital Signature Algorithm
(ECDSA) on the secp256k1 curve.

Two modules are provided:

1. An OpenSSL-using module that's available if OpenSSL is available on
   the system: `two1.lib.crypto.ecdsa_openssl`

2. A pure python module that's always available and is very portable,
   but which doesn't contain as many performance optimizations and which
   has not been as well audited as the Bitcoin-related parts of OpenSSL:
   `two1.lib.crypto.ecdsa`

Submodules
----------

.. toctree::

    two1.lib.crypto.submodules

A simple example:

    >>> from two1.lib.crypto import ecdsa
    >>> ec = ecdsa.secp256k1()
    >>>
    >>> ## Generate ECDSA key pair from random
    >>> priv, pub = ec.gen_key_pair()
    >>> ## Private key
    >>> priv
    3847872623548319391455692167473247674183946521467832802482786839851919968799
    >>> ## Public key, x coordinate and then y coordinate
    >>> pub.x
    2415082117413395476165664856824912483567021584059887816816320242542362529060
    >>> pub.y
    10353152122150796736951723708916428234072509795738767586951937235484200709278
    >>> ## Public key, compressed
    >>> pub.compressed_bytes
    b'\x02\xf4\xf5\xbc\x9d{\x91+c\xb2\xffO;\x14)\xed3E\x11\xad+\xab\xc3\x1c\x1b\xe7\xd5\xc2%\x1b\xc8\xe9\x8b'
    >>>
    >>> ## Recover the two possible y coordinates from the x coordinate, as
    >>> ## necessary when using compressed keys
    >>> ec.y_from_x(pub.x)
    [10353152122150796736951723708916428234072509795738767586951937235484200709278,
    105438937115165398686619261299771479619197474869901796452505646772424633962385]
    >>>
    >>> ## Sign a message
    >>> signature = ec.sign(b'21', priv)
    >>> signature
    (Point(x=48170274459291977398620592594153137413292379572661653951252377159885526334606,
    y=25099180716939036749527356364397603957892864939606910246337660310599408353076),
    1)
    >>>
    >>> ## Verify the signature
    >>> ec.verify(b'21', signature.__getitem__(0), pub)
    True
