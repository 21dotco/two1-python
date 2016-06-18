from ctypes import c_int
from ctypes import c_char_p
from ctypes import c_long
from ctypes import c_void_p
from ctypes import create_string_buffer
from ctypes import CDLL
from ctypes import POINTER
from ctypes import Structure

import math
import platform


class OpenSSLSignature(Structure):
    _fields_ = [("r", c_void_p),
                ("s", c_void_p)]

sys_type = platform.system()
if sys_type == "Darwin":
    libcrypto = CDLL('libcrypto.dylib')
elif sys_type == "Linux":
    libcrypto = CDLL('libcrypto.so')
else:
    raise Exception("Unsupported platform %s" % sys_type)

lc = libcrypto

lc.OBJ_sn2nid.argtypes = [c_char_p]
lc.OBJ_sn2nid.restype = c_int

lc.EC_KEY_new_by_curve_name.restype = c_void_p
lc.EC_KEY_generate_key.argtypes = [c_void_p]
lc.EC_KEY_generate_key.restype = c_int
lc.EC_KEY_check_key.argtypes = [c_void_p]
lc.EC_KEY_check_key.restype = c_int
lc.EC_KEY_get0_private_key.argtypes = [c_void_p]
lc.EC_KEY_get0_private_key.restype = c_void_p
lc.EC_KEY_get0_public_key.argtypes = [c_void_p]
lc.EC_KEY_get0_public_key.restype = c_void_p
lc.EC_KEY_set_private_key.argtypes = [c_void_p, c_void_p]
lc.EC_KEY_set_private_key.restype = c_int
lc.EC_KEY_set_public_key.argtypes = [c_void_p, c_void_p]
lc.EC_KEY_set_public_key.restype = c_int
lc.EC_KEY_get0_group.argtypes = [c_void_p]
lc.EC_KEY_get0_group.restype = c_void_p
lc.EC_KEY_free.argtypes = [c_void_p]

lc.EC_GROUP_new_by_curve_name.restype = c_void_p
lc.EC_GROUP_get_order.argtypes = [c_void_p] * 3
lc.EC_GROUP_get_order.restype = c_int
lc.EC_GROUP_get_curve_GFp.argtypes = [c_void_p] * 5
lc.EC_GROUP_get_curve_GFp.restype = c_int
lc.EC_GROUP_free.argtypes = [c_void_p]

lc.EC_POINT_new.argtypes = [c_void_p]
lc.EC_POINT_new.restype = c_void_p
lc.EC_POINT_point2oct.argtypes = [c_void_p]
lc.EC_POINT_point2oct.restype = c_int
lc.EC_POINT_mul.argtypes = [c_void_p] * 6
lc.EC_POINT_mul.restype = c_int
lc.EC_POINT_invert.argtypes = [c_void_p] * 3
lc.EC_POINT_invert.restype = c_int
lc.EC_POINT_get_affine_coordinates_GFp.argtypes = [c_void_p] * 5
lc.EC_POINT_set_affine_coordinates_GFp.argtypes = [c_void_p] * 5
lc.EC_POINT_set_affine_coordinates_GFp.restype = c_int
lc.EC_POINT_set_compressed_coordinates_GFp.argtypes = [
    c_void_p, c_void_p, c_void_p, c_int, c_void_p]
lc.EC_POINT_set_compressed_coordinates_GFp.restype = c_int
lc.EC_POINT_is_at_infinity.argtypes = [c_void_p, c_void_p]
lc.EC_POINT_is_at_infinity.restype = c_int
lc.EC_POINT_set_to_infinity.argtypes = [c_void_p, c_void_p]
lc.EC_POINT_set_to_infinity.restype = c_int
lc.EC_POINT_is_on_curve.argtypes = [c_void_p] * 3
lc.EC_POINT_is_on_curve.restype = c_int

lc.d2i_ECDSA_SIG.argtypes = [c_void_p, c_void_p, c_long]
lc.d2i_ECDSA_SIG.restype = POINTER(OpenSSLSignature)
lc.ECDSA_SIG_new.argtypes = []
lc.ECDSA_SIG_new.restype = POINTER(OpenSSLSignature)
lc.ECDSA_SIG_free.argtypes = [POINTER(OpenSSLSignature)]
lc.ECDSA_do_sign_ex.argtypes = [
    c_char_p, c_int, c_void_p, c_void_p, c_void_p]
lc.ECDSA_do_sign_ex.restype = POINTER(OpenSSLSignature)
lc.ECDSA_do_verify.argtypes = [
    c_void_p, c_int, POINTER(OpenSSLSignature), c_void_p]
lc.ECDSA_do_verify.restype = c_int

lc.BN_new.restype = c_void_p
lc.BN_num_bits.argtypes = [c_void_p]
lc.BN_num_bits.restype = c_int
lc.BN_bn2bin.argtypes = [c_void_p, c_char_p]
lc.BN_bn2bin.restype = c_int
lc.BN_bin2bn.argtypes = [c_char_p, c_int, c_void_p]
lc.BN_bin2bn.restype = c_void_p
lc.BN_mod_mul.argtypes = [c_void_p] * 5
lc.BN_mod_mul.restype = c_int
lc.BN_mod_add.argtypes = [c_void_p] * 5
lc.BN_mod_add.restype = c_int
lc.BN_mod_inverse.argtypes = [c_void_p] * 4
lc.BN_mod_inverse.restype = c_void_p
lc.BN_free.argtypes = [c_void_p]
lc.BN_CTX_new.restype = c_void_p
lc.BN_CTX_start.argtypes = [c_void_p]
lc.BN_CTX_get.argtypes = [c_void_p]
lc.BN_CTX_get.restype = c_void_p
lc.BN_CTX_end.argtypes = [c_void_p]
lc.BN_CTX_free.argtypes = [c_void_p]

lc.ERR_load_crypto_strings()


def get_curve_params(group):
    """ Retrieves all elliptic curve parameters

    Args:
        group (c_void_p): The OpenSSL group (curve) to
            retrieve the parameters for.

    Returns:
        dict: With the following key/value pairs:
            p: Prime defining the field
            a: Linear coefficient of the curve
            b: Curve constant
            n: Curve order
            h: Curve co-factor
    """
    ctx = c_void_p(lc.BN_CTX_new())
    lc.BN_CTX_start(ctx)

    order_bn = c_void_p(lc.BN_CTX_get(ctx))
    cofactor_bn = c_void_p(lc.BN_CTX_get(ctx))
    p_bn = c_void_p(lc.BN_CTX_get(ctx))
    a_bn = c_void_p(lc.BN_CTX_get(ctx))
    b_bn = c_void_p(lc.BN_CTX_get(ctx))
    lc.EC_GROUP_get_order(group, order_bn, c_void_p())
    lc.EC_GROUP_get_cofactor(group, cofactor_bn, c_void_p())
    lc.EC_GROUP_get_curve_GFp(group, p_bn, a_bn, b_bn, ctx)

    rv = {}
    rv['p'] = bn_to_int(p_bn)
    rv['a'] = bn_to_int(a_bn)
    rv['b'] = bn_to_int(b_bn)
    rv['n'] = bn_to_int(order_bn)
    rv['h'] = bn_to_int(cofactor_bn)

    lc.BN_CTX_end(ctx)
    lc.BN_CTX_free(ctx)

    return rv


def new_key(curve_name, private_key=None):
    """ Generates a new EC_KEY

    Args:
        curve_name (int): The OpenSSL identifier of the curve which
            the key will be part of.
        private_key (int): If not provided, a random key pair will be
            generated. Otherwise, the key will be initiated with the
            provided private key (and corresponding public key)

    Returns:
        c_void_p: An opaque pointer to the new EC_KEY object. The
            caller is responsible for freeing the key object.
    """
    k = c_void_p(lc.EC_KEY_new_by_curve_name(curve_name))

    if private_key is None:
        lc.EC_KEY_generate_key(k)
    else:
        key_ok = set_private_key_from_int(k, private_key)
        if not key_ok:
            raise ValueError("Key is not ok")

    return k


def get_private_key_bytes(key):
    """ Retrieves the bytes corresponding to the private key.

    Args:
        key (c_void_p): A pointer to an EC_KEY object.

    Returns:
        bytes: A byte stream containing the private key.
    """
    priv_key_bn = c_void_p(lc.EC_KEY_get0_private_key(key))
    priv_key_bytes = bn_to_bytes(priv_key_bn)

    return priv_key_bytes


def get_private_key_int(key):
    """ Retrieves the integer corresponding to the private key.

    Args:
        key (c_void_p): A pointer to an EC_KEY object.

    Returns:
        int: The integer representation of the private key.
    """
    rv = None
    b = get_private_key_bytes(key)
    if b is not None:
        rv = int.from_bytes(b, byteorder='big')

    return rv


def set_private_key_from_bytes(key, b):
    """ Sets the private portion of key from b.

        This function also sets the public key portion of
        key after computing the public key from the provided
        bytes of the private key.

    Args:
        key (c_void_p): A pointer to an EC_KEY object.
        b (bytes): The bytes representing the private key.

    Returns:
        bool: Whether key passes OpenSSL's sanity checks after
            both private & public keys are set.
    """
    priv_bn = bytes_to_bn(b)

    group = c_void_p(lc.EC_KEY_get0_group(key))

    lc.EC_KEY_set_private_key(key, priv_bn)

    # Now jam the public key
    pub_pt = c_void_p(lc.EC_POINT_new(group))
    lc.EC_POINT_mul(group,
                    pub_pt,
                    priv_bn,
                    c_void_p(),
                    c_void_p(),
                    c_void_p())
    lc.EC_KEY_set_public_key(key, pub_pt)

    lc.EC_POINT_free(pub_pt)

    return lc.EC_KEY_check_key(key)


def set_private_key_from_int(key, i, size=32):
    """ Sets the private portion of key from i.

        This function also sets the public key portion of
        key after computing the public key from the provided
        private key.

    Args:
        key (c_void_p): A pointer to an EC_KEY object.
        i (int): The integer representing the private key.
        size (int): Size in bytes the key should be.

    Returns:
        bool: Whether key passes OpenSSL's sanity checks after
            both private & public keys are set.
    """
    b = i.to_bytes(size, byteorder='big')
    return set_private_key_from_bytes(key, b)


def bn_to_bytes(bn):
    """ Translates an OpenSSL big number (BN) to bytes.

    Args:
        bn (c_void_p): A pointer to an OpenSSL BN object.

    Returns:
        bytes: The bytes corresponding to the BN object. It is
            returned as a big-endian positive number.
    """
    size = math.ceil(lc.BN_num_bits(bn) / 8.0)
    b = create_string_buffer(b'\x00' * size)
    lc.BN_bn2bin(bn, b)

    return b[:size]


def bytes_to_bn(b, bn=None):
    """ Translates bytes to an OpenSSL big number (BN).

    Args:
        b (bytes): Big-endian, positive number to translate.
        bn (c_void_p): If not None, sets it to the number represented
            by b.

    Returns:
        c_void_p: If bn is None, a pointer to a new OpenSSL BN object,
             otherwise bn. In all cases, the caller is responsible for
             freeing the memory associated with the OpenSSL object.
    """
    buf = create_string_buffer(b)
    return c_void_p(lc.BN_bin2bn(buf, len(b), bn))


def bn_to_int(bn):
    """ Translates an OpenSSL big number (BN) to a Python integer.

    Args:
        bn (c_void_p): A pointer to an OpenSSL BN object.

    Returns:
        int: The python integer corresponding to the BN object.
    """
    return int.from_bytes(bn_to_bytes(bn), byteorder='big')


def int_to_bn(i, bn=None, size=32):
    """ Translates a python integer to an OpenSSL big number (BN).

    Args:
        i (int): Integer to translate.
        bn (c_void_p): If not None, sets it to the number represented
            by i.
        size (int): The maximal byte-length of i.

    Returns:
        c_void_p: If bn is None, a pointer to a new OpenSSL BN object,
             otherwise bn. In all cases, the caller is responsible for
             freeing the memory associated with the OpenSSL object.
    """
    return bytes_to_bn(i.to_bytes(size, byteorder='big'), bn)


def point_get_xy_bytes(group, pt):
    """ Gets bytes for x and y components of an EC_POINT.

        This uses `bn_to_bytes` to create the bytes objects after
        extracting the x and y components of pt.

    Args:
        group (c_void_p): An opaque pointer to the group (curve) that
            pt is part of.
        pt (c_void_p): An opaque pointer to the OpenSSL EC_POINT object.

    Returns:
        tuple: Containing the x bytes, y bytes and a boolean representing
            whether the point is at infinity or not.
    """
    x_bn = c_void_p(lc.BN_new())
    y_bn = c_void_p(lc.BN_new())
    lc.EC_POINT_make_affine(group, pt, c_void_p(None))
    lc.EC_POINT_get_affine_coordinates_GFp(group,
                                           pt,
                                           x_bn,
                                           y_bn,
                                           c_void_p(None))
    inf = bool(lc.EC_POINT_is_at_infinity(group, pt))

    x_bytes = bn_to_bytes(x_bn)
    y_bytes = bn_to_bytes(y_bn)

    lc.BN_free(x_bn)
    lc.BN_free(y_bn)

    return (x_bytes, y_bytes, inf)


def point_get_xy_ints(group, pt):
    """ Gets the x and y components of an EC_POINT.

    Args:
        group (c_void_p): An opaque pointer to the group (curve) that
            pt is part of.
        pt (c_void_p): An opaque pointer to the OpenSSL EC_POINT object.

    Returns:
        tuple: Containing x, y and a boolean representing whether the
            point is at infinity or not.
    """
    x_b, y_b, inf = point_get_xy_bytes(group, pt)
    x = int.from_bytes(x_b, byteorder='big')
    y = int.from_bytes(y_b, byteorder='big')

    return (x, y, inf)


def point_new_from_bytes(group, x_bytes, y_bytes, infinity=False):
    """ Creates a new OpenSSL EC_POINT from bytes.

    Args:
        group (c_void_p): An opaque pointer to the group (curve) that
            the point should be part of.
        x_bytes (bytes): Big-endian, positive byte representation of x.
        y_bytes (bytes): Big-endian, positive byte representation of y.
        infinity (bool): True if the point is at infinity, False otherwise.

    Returns:
        c_void_p: An opaque pointer to the newly constructed OpenSSL
            EC_POINT object. The caller bears responsibility for freeing
            the memory associated with the returned object.
    """
    pt = c_void_p(lc.EC_POINT_new(group))

    x_bn = bytes_to_bn(x_bytes)
    y_bn = bytes_to_bn(y_bytes)

    res = lc.EC_POINT_set_affine_coordinates_GFp(group,
                                                 pt,
                                                 x_bn,
                                                 y_bn,
                                                 c_void_p(None))
    if not res:
        lc.EC_POINT_free(pt)
        return None

    if infinity:
        lc.EC_POINT_set_to_infinity(group, pt)

    return pt


def point_new_from_ints(group, x, y, infinity=False, size=32):
    """ Creates a new OpenSSL EC_POINT from x & y integers.

    Args:
        group (c_void_p): An opaque pointer to the group (curve) that
            the point should be part of.
        x_bytes (bytes): Big-endian, positive byte representation of x.
        y_bytes (bytes): Big-endian, positive byte representation of y.
        infinity (bool): True if the point is at infinity, False otherwise.
        size (int): Maximal byte-length of x and y.

    Returns:
        c_void_p: An opaque pointer to the newly constructed OpenSSL
            EC_POINT object. The caller bears responsibility for freeing
            the memory associated with the returned object.
    """
    x_bytes = x.to_bytes(size, byteorder='big')
    y_bytes = y.to_bytes(size, byteorder='big')

    return point_new_from_bytes(group, x_bytes, y_bytes, infinity)


def get_public_key_bytes(key):
    """ Returns the bytes corresponding to the public key coordinates.

    Args:
        key (c_void_p): An opaque pointer to an OpenSSL EC_KEY object.

    Returns:
        tuple: Containing bytes for x & y public key components and a
            boolean indicating whether the point is at infinity or not.
    """
    group = c_void_p(lc.EC_KEY_get0_group(key))
    pub_key_point = c_void_p(lc.EC_KEY_get0_public_key(key))
    x_b, y_b, inf = point_get_xy_bytes(group, pub_key_point)

    return (x_b, y_b, inf)


def get_public_key_ints(key):
    """ Returns the integers corresponding to the public key coordinates.

    Args:
        key (c_void_p): An opaque pointer to an OpenSSL EC_KEY object.

    Returns:
        tuple: Containing the x & y public key components and a
            boolean indicating whether the point is at infinity or not.
    """
    xb, yb, inf = get_public_key_bytes(key)
    x = int.from_bytes(xb, byteorder='big')
    y = int.from_bytes(yb, byteorder='big')

    return (x, y, inf)


def set_public_key_from_bytes(key, x_bytes, y_bytes, infinity):
    """ Sets the public key portion of an OpenSSL EC_KEY object from
        bytes representations of the x & y components of the public key.

    Args:
        key (c_void_p): An opaque pointer to an OpenSSL EC_KEY object.
        x_bytes (bytes): Big-endian, positive byte-representation of the
            x component of the public-key point.
        y_bytes (bytes): Big-endian, positive byte-representation of the
            y component of the public-key point.
        infinity (bool): True if the point is at infinity, False otherwise.

    Returns:
        bool: True if the public key was set properly, False otherwise.
    """
    group = c_void_p(lc.EC_KEY_get0_group(key))
    pub_pt = point_new_from_bytes(group, x_bytes, y_bytes, infinity)
    res = lc.EC_KEY_set_public_key(key, pub_pt)

    return bool(res)


def set_public_key_from_ints(key, x, y, infinity, size=32):
    """ Sets the public key portion of an OpenSSL EC_KEY object from
        bytes representations of the x & y components of the public key.

    Args:
        key (c_void_p): An opaque pointer to an OpenSSL EC_KEY object.
        x (int): X component of the public-key point.
        y (int): Y component of the public-key point.
        infinity (bool): True if the point is at infinity, False otherwise.
        size (int): Maximal byte-size of x and y.

    Returns:
        bool: True if the public key was set properly, False otherwise.
    """
    x_bytes = x.to_bytes(size, byteorder='big')
    y_bytes = y.to_bytes(size, byteorder='big')
    return set_public_key_from_bytes(key,
                                     x_bytes,
                                     y_bytes,
                                     infinity)


def sig_new_from_bytes(r_bytes, s_bytes):
    """ Creates a new OpenSSL ECDSA_SIG structure from r & s bytes.

    Args:
        r_bytes (bytes): Big-endian, positive byte-representation of the
            r component of the signature.
        s_bytes (bytes): Big-endian, positive byte-representation of the
            s component of the signature.

    Returns:
        c_void_p: An opaque pointer to a new OpenSSL ECDSA_SIG structure
            represented by the `OpenSSLSignature` class.
    """
    sig = lc.ECDSA_SIG_new()

    r_buf = create_string_buffer(r_bytes)
    s_buf = create_string_buffer(s_bytes)
    lc.BN_bin2bn(r_buf, len(r_bytes), sig.contents.r)
    lc.BN_bin2bn(s_buf, len(s_bytes), sig.contents.s)

    return sig


def sig_new_from_ints(r, s, size=32):
    """ Creates a new OpenSSL ECDSA_SIG structure from r & s integers.

    Args:
        r (int): R component of the signature.
        s (int): S component of the signature.
        size (int): Maximal byte-size of r & s.

    Returns:
        c_void_p: An opaque pointer to a new OpenSSL ECDSA_SIG structure
            represented by the `OpenSSLSignature` class.
    """
    return sig_new_from_bytes(r_bytes=r.to_bytes(size, byteorder='big'),
                              s_bytes=s.to_bytes(size, byteorder='big'))
