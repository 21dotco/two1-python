The 21 Crypto Library (``two1.crypto``)
===========================================
The crypto module within the 21 Bitcoin Library (``two1.crypto``)
provides an interface to the low-level cryptographic functions used in
Bitcoin to create public keys and signatures using the Elliptic Curve
Digital Signature Algorithm (ECDSA) on the secp256k1 curve.

Two modules are provided:

1. `two1.crypto.ecdsa_openssl`: An OpenSSL-using module that's
   available if OpenSSL is available on the system.

2. `two1.crypto.ecdsa`: A pure Python module that's always
   available and is very portable, but which does not contain as many
   performance optimizations and which has not been as well audited as
   the Bitcoin-related parts of OpenSSL.
   
Quickstart
==========
We will illustrate the use of the ``two1.crypto`` module by going
through a simple example:

Generate an ECDSA key pair
--------------------------
Start our simple example by importing the library and loading the
secp256k1 elliptical curve Bitcoin uses for cryptography::

  >>> from two1.crypto import ecdsa
  >>> ec = ecdsa.secp256k1()

Generate an ECDSA key pair from random data, which is the way all non-HD
wallets generate keys::

  >>> priv, pub = ec.gen_key_pair()

Show the private key::

  >>> priv
  3847872623548319391455692167473247674183946521467832802482786839851919968799

Public keys are points on the secp256k1 curve; they're represented by
x,y coordinates on a 256-bit by 256-bit prime number field.::

  >>> pub.x
  2415082117413395476165664856824912483567021584059887816816320242542362529060
  >>> pub.y
  10353152122150796736951723708916428234072509795738767586951937235484200709278

The construction of the secp256k1 and other Koblitz-style curves means
that the curve never backtracks itself, so each x coordinate only has
two possible y coordinates (the inverse of each other).  This allows us
to "compress" the y coordinate down to a single bit: whether the
coordinate is on the "high" half of the curve or the "low" half of the curve.
Let's get the compressed public key for the same key above::

  >>> pub.compressed_bytes
  b'\x02\xf4\xf5\xbc\x9d{\x91+c\xb2\xffO;\x14)\xed3E\x11\xad+\xab\xc3\x1c\x1b\xe7\xd5\xc2%\x1b\xc8\xe9\x8b'

Just in case you lose that extra bit of information telling you which y
coordinate is correct, you can recover both possible y coordinates for any x
coordinate on the curve::

  >>> ec.y_from_x(pub.x)
  [10353152122150796736951723708916428234072509795738767586951937235484200709278,
  105438937115165398686619261299771479619197474869901796452505646772424633962385]

How to sign a message
---------------------
Generally we use these keys for signing and verifying things within Bitcoin. Let's sign a
message::

  >>> signature = ec.sign(b'21', priv)
  >>> signature
  (Point(x=48170274459291977398620592594153137413292379572661653951252377159885526334606,
  y=25099180716939036749527356364397603957892864939606910246337660310599408353076),
  1)

How to verify a signature
-------------------------
The signature gives us a new point on the secp256k1 curve.  Now let's
verify that signature::

  >>> ec.verify(b'21', signature.__getitem__(0), pub)
  True

``two1.crypto``: module contents
====================================
The ``two1.crypto`` module is organized into the following submodules:
   
.. toctree::

   two1.crypto.submodules
