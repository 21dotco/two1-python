two1.crypto.ecdsa
---------------------
For the vast majority of use cases, importing either `EllipticCurve`
or `secp256k1` from `two1.crypto.ecdsa` should be sufficient. The
module will automatically use `ecdsa_openssl` if OpenSSL is installed
and usable on the system. If it is not installed/usable,
`ecdsa_python` will be used instead.

To directly select one or the other, import specifically from
`two1.crypto.ecdsa_openssl` or `two1.crypto.ecdsa_python`.

.. automodule:: two1.crypto.ecdsa_openssl
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: two1.crypto.ecdsa_python
    :members:
    :undoc-members:
    :show-inheritance:
