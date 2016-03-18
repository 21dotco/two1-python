try:
    from two1.crypto import ecdsa_openssl as _ecdsa
except:
    from two1.crypto import ecdsa_python as _ecdsa

ECPointAffine = _ecdsa.ECPointAffine
EllipticCurve = _ecdsa.EllipticCurve
secp256k1 = _ecdsa.secp256k1
