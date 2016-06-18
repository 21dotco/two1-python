"""This submodule provides functions for accomplishing common tasks encountered
in creating and parsing Bitcoin objects, like turning difficulties into targets
or deserializing and serializing various kinds of packed byte formats."""
import base58
import codecs
import hashlib
import random
import struct
import os

MAX_TARGET = 0x00000000FFFF0000000000000000000000000000000000000000000000000000


def rand_bytes(n, secure=True):
    """ Returns n random bytes.

    Args:
        n (int): number of bytes to return.
        secure (bool): If True, uses os.urandom to generate
            cryptographically secure random bytes. Otherwise, uses
            random.randint() which generates pseudo-random numbers.

    Returns:
        b (bytes): n random bytes.
    """
    if secure:
        return os.urandom(n)
    else:
        return bytes([random.randint(0, 255) for i in range(n)])


def bytes_to_str(b):
    """ Converts bytes into a hex-encoded string.

    Args:
        b (bytes): bytes to encode

    Returns:
        h (str): hex-encoded string corresponding to b.
    """
    return codecs.encode(b, 'hex_codec').decode('ascii')


def hex_str_to_bytes(h):
    """ Converts a hex-encoded string to bytes.

    Args:
        h (str): hex-encoded string to convert.

    Returns:
        b (bytes): bytes corresponding to h.
    """
    return bytes.fromhex(h)


# Is there a better way of doing this?
def render_int(n):
    """ Renders an int in the shortest possible form.

    When packing the height into the coinbase script, the integer
    representing the height must be encoded in the shortest possible
    manner. See: https://bitcoin.org/en/developer-reference#coinbase.

    Args:
        n (int): number to be encoded.

    Returns:
        b (bytes): bytes representing n in the shortest possible form.
    """
    # little-endian byte stream
    if n < 0:
        neg = True
        n = -n
    else:
        neg = False
    r = []
    while n:
        r.append(n & 0xff)
        n >>= 8
    if neg:
        if r[-1] & 0x80:
            r.append(0x80)
        else:
            r[-1] |= 0x80
    elif r and (r[-1] & 0x80):
        r.append(0)
    return bytes(r)


def pack_compact_int(i):
    """ See
    https://bitcoin.org/en/developer-reference#compactsize-unsigned-integers

    Args:
        i (int): Integer to be serialized.

    Returns:
        b (bytes): Serialized bytes corresponding to i.
    """
    if i < 0xfd:
        return struct.pack('<B', i)
    elif i <= 0xffff:
        return struct.pack('<BH', 0xfd, i)
    elif i <= 0xffffffff:
        return struct.pack('<BI', 0xfe, i)
    else:
        return struct.pack('<BQ', 0xff, i)


def unpack_compact_int(bytestr):
    """ See
    https://bitcoin.org/en/developer-reference#compactsize-unsigned-integers

    Args:
        bytestr (bytes): bytes containing an unsigned integer to be
            deserialized.

    Returns:
        n (int): deserialized integer.
    """

    b0 = bytestr[0]
    if b0 < 0xfd:
        return (b0, bytestr[1:])
    elif b0 == 0xfd:
        return (struct.unpack('<H', bytestr[1:3])[0], bytestr[3:])
    elif b0 == 0xfe:
        return (struct.unpack('<I', bytestr[1:5])[0], bytestr[5:])
    elif b0 == 0xff:
        return (struct.unpack('<Q', bytestr[1:9])[0], bytestr[9:])
    else:
        return None


def pack_u32(i):
    """ Serializes a 32-bit integer into little-endian form.

    Args:
        i (int): integer to be serialized.

    Returns:
        b (bytes): 4 bytes containing the little-endian serialization of i.
    """
    return struct.pack('<I', i)


def unpack_u32(b):
    """ Deserializes a 32-bit integer from bytes.

    Args:
        b (bytes): At least 4 bytes containing the serialized integer.

    Returns:
        (i, b) (tuple): A tuple containing the deserialized integer and the
        remainder of the byte stream.
    """
    u32 = struct.unpack('<I', b[0:4])
    return (u32[0], b[4:])


def pack_u64(i):
    """ Serializes a 64-bit integer into little-endian form.

    Args:
        i (int): integer to be serialized.

    Returns:
        b (bytes): 8 bytes containing the little-endian serialization of i.
    """
    return struct.pack('<Q', i)


def unpack_u64(b):
    """ Deserializes a 64-bit integer from bytes.

    Args:
        b (bytes): At least 8 bytes containing the serialized integer.

    Returns:
        (i, b) (tuple): A tuple containing the deserialized integer and the
        remainder of the byte stream.
    """
    u64 = struct.unpack('<Q', b[0:8])
    return (u64[0], b[8:])


def pack_var_str(s):
    """ Serializes a variable length byte stream.

    Args:
        s (bytes): byte stream to serialize

    Return:
        b (bytes): Serialized bytes, prepended with the length of the
        byte stream.
    """
    return pack_compact_int(len(s)) + s


def unpack_var_str(b):
    """ Deserializes a variable length byte stream.

    Args:
        b (bytes): variable length byte stream to deserialize

    Returns:
        (s, b) (tuple): A tuple containing the variable length byte stream
        and the remainder of the input byte stream.
    """
    strlen, b0 = unpack_compact_int(b)
    return (b0[:strlen], b0[strlen:])


def bits_to_target(bits):
    """ Decodes the full target from a compact representation.
    See: https://bitcoin.org/en/developer-reference#target-nbits

    Args:
        bits (int): Compact target (32 bits)

    Returns:
        target (Bignum): Full 256-bit target
    """
    shift = bits >> 24
    target = (bits & 0xffffff) * (1 << (8 * (shift - 3)))
    return target


def bits_to_difficulty(bits):
    """ Determines the difficulty corresponding to bits.
    See: https://en.bitcoin.it/wiki/Difficulty

    Args:
        bits (int): Compact target (32 bits)

    Returns:
        diff (float): Measure of how hard it is to find a solution
        below the target represented by bits.
    """
    target = bits_to_target(bits)
    return MAX_TARGET / target


def difficulty_to_target(difficulty):
    """ Converts a difficulty to a long-form target.

    Args:
        difficulty (float): The difficulty to return the appropriate target for

    Returns:
        target (int): The corresponding target
    """
    return int(MAX_TARGET / difficulty)


def target_to_bits(target):
    """ Creates a compact target representation for a given target.

    Args:
        target (Bignum): The long-form target to make compact.

    Returns:
        ct (int): Compact target
    """
    # Get bit length
    nbits = target.bit_length()
    # Round up to next 8-bits
    nbits = ((nbits + 7) & ~0x7)
    exponent = (int(nbits/8) & 0xff)
    coefficient = (target >> (nbits - 24)) & 0xffffff
    if coefficient & 0x800000:
        coefficient >>= 8
        exponent += 1
    return (exponent << 24) | coefficient


def difficulty_to_bits(difficulty):
    """ Converts a difficulty to a compact target.

    Args:
        difficulty (float): The difficulty to create a target for

    Returns:
        ct (int): Compact target
    """
    return target_to_bits(difficulty_to_target(difficulty))


def address_to_key_hash(s):
    """ Given a Bitcoin address decodes the version and
    RIPEMD-160 hash of the public key.

    Args:
        s (bytes): The Bitcoin address to decode

    Returns:
        (version, h160) (tuple): A tuple containing the version and
        RIPEMD-160 hash of the public key.
    """
    n = base58.b58decode_check(s)
    version = n[0]
    h160 = n[1:]
    return version, h160


def key_hash_to_address(hash160, version=0x0):
    """Convert RIPEMD-160 hash to bitcoin address.

    Args:
        hash160 (bytes/str): bitcoin hash160 to decode
        version (int): The version prefix

    Returns:
        (bitcoin address): base58 encoded bitcoin address
    """
    if isinstance(hash160, str):
        # if 0x in string, strip it
        if "0x" in hash160:
            h160 = hex_str_to_bytes(hash160[2:])
        else:
            h160 = hex_str_to_bytes(hash160)
    elif isinstance(hash160, bytes):
        h160 = hash160

    address = base58.b58encode_check(bytes([version]) + h160)
    return address


def hash160(b):
    """ Computes the HASH160 of b.

    Args:
        b (bytes): A byte string to compute the HASH160 of.

    Returns:
        The RIPEMD-160 digest of the SHA256 hash of b.
    """
    r = hashlib.new('ripemd160')
    r.update(hashlib.sha256(b).digest())

    return r.digest()


def compute_reward(height):
    """ Computes the block reward for a block at the supplied height.
    See: https://en.bitcoin.it/wiki/Controlled_supply for the reward
    schedule.

    Args:
        height (int): Block height

    Returns:
        reward (int): Number of satoshis rewarded for solving a block at the
        given height.
    """
    base_subsidy = 50 * 100000000
    era = height // 210000
    if era == 0:
        return base_subsidy
    return int(base_subsidy / 2 ** era)
