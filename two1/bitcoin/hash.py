"""this submodule provides a Hash class for interacting with SHA-256 hashes
in a user-friendly way."""
import hashlib

from two1.bitcoin.utils import bytes_to_str


class Hash(object):
    """ Wrapper around a byte string for handling SHA-256 hashes used
        in bitcoin. Specifically, this class is useful for disambiguating
        the required hash ordering.

        This assumes that a hex string is in RPC order and a
        byte string is in internal order. If `h` is bytes, `h` is
        assumed to already be in internal order and this function is
        effectively a no-op.

    Args:
        h (bytes or str): the hash to convert.

    Returns:
        Hash: a Hash object.
    """

    @staticmethod
    def dhash(b):
        """ Computes the double SHA-256 hash of b.

        Args:
            b (bytes): The bytes to double-hash.

        Returns:
            Hash: a hash object containing the double-hash of b.
        """
        return Hash(hashlib.sha256(hashlib.sha256(b).digest()).digest())

    def __init__(self, h):
        if isinstance(h, bytes):
            if len(h) != 32:
                raise ValueError("h must be 32 bytes long")
            self._bytes = h
        elif isinstance(h, str):
            if len(h) != 64:
                raise ValueError("h must be 32 bytes (64 hex chars) long")
            self._bytes = bytes.fromhex(h)[::-1]
        else:
            raise TypeError("h must be either a str or bytes")

    def __bytes__(self):
        return self._bytes

    def __eq__(self, b):
        if isinstance(b, bytes):
            return self._bytes == b
        elif isinstance(b, Hash):
            return self._bytes == b._bytes
        elif isinstance(b, str):
            return self._bytes == Hash(b)._bytes
        else:
            raise TypeError("b must be either a Hash object or bytes")

    def __str__(self):
        """ Returns a hex string in RPC order
        """
        return bytes_to_str(self._bytes[::-1])

    def to_int(self, endianness='big'):
        """ Returns an integer representation of the Hash.

        Args:
            endianness (Optional[int]): whether to interpret the underlying
                byte string as little- or big-endian before converting it to an
                integer. Defaults to 'big'.
        """
        if endianness in ['big', 'little']:
            return int.from_bytes(bytes(self), endianness)
        else:
            raise ValueError("endianness must be either 'big' or 'little'.")
