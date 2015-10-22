from collections import namedtuple
import hmac
import random


Point = namedtuple('Point', ['x', 'y'])


class EllipticCurveBase(object):
    """ A generic class for elliptic curves and operations on them.

        The curves must be of the form: y^2 = x^3 + a*x + b.
    """

    def __init__(self, hash_function):
        self.hash_function = hash_function

    def is_on_curve(self, p):
        """ Checks whether a point is on the curve.

        Args:
            p (ECPointAffine): Point to be checked

        Returns:
            bool: True if p is on the curve, False otherwise.
        """
        raise NotImplementedError

    def y_from_x(self, x):
        """ Computes the y component corresponding to x.

            Since elliptic curves are symmetric about the x-axis,
            the x component (and sign) is all that is required to determine
            a point on the curve.

        Args:
            x (int): x component of the point.

        Returns:
            tuple: both possible y components of the point.
        """
        raise NotImplementedError

    def gen_key_pair(self, random_generator=random.SystemRandom()):
        """ Generates a public/private key pair.

        Args:
            random_generator (generator): The random generator to use.
        Returns:
            tuple: A private key in the range of 1 to `self.n - 1`
               and an ECPointAffine containing the public key point.
        """
        raise NotImplementedError

    def public_key(self, private_key):
        """ Returns the public (verifying) key for a given private key.

        Args:
            private_key (int): the private key to derive the public key for.

        Returns:
            ECPointAffine: The point representing the public key.
        """
        raise NotImplementedError

    def recover_public_key(self, message, signature, recovery_id=None):
        """ Recovers possibilities for the public key associated with the
            private key used to sign message and generate signature.

            Since there are multiple possibilities (two for curves with
            co-factor = 1), each possibility that successfully verifies the
            signature is returned.
        Args:
           message (bytes): The message that was signed.
           signature (ECPointAffine): The point representing the signature.
           recovery_id (int) (Optional): If provided, limits the valid x and y
              point to only that described by the recovery_id.

        Returns:
           list(ECPointAffine): List of points representing valid public
              keys that verify signature.
        """
        raise NotImplementedError

    def _sign(self, message, private_key, do_hash=True, secret=None):
        raise NotImplementedError

    def sign(self, message, private_key, do_hash=True):
        """ Signs a message with the given private key.

        Args:
            message (bytes): The message to be signed
            private_key (int): Integer that is the private key
            do_hash (bool): True if the message should be hashed prior
                to signing, False if not. This should always be left as
                True except in special situations which require doing
                the hash outside (e.g. handling Bitcoin bugs).

        Returns:
            (Point, int): The point (r, s) representing the signature
                and the ID representing which public key possibility
                is associated with the private key being used to sign.
        """
        return self._sign(message, private_key, do_hash)

    def verify(self, message, signature, public_key, do_hash=True):
        """ Verifies that signature was generated with a private key corresponding
            to public key, operating on message.

        Args:
            message (bytes): The message to be signed
            signature (Point): (r, s) representing the signature
            public_key (ECPointAffine): ECPointAffine of the public key
            do_hash (bool): True if the message should be hashed prior
               to signing, False if not. This should always be left as
               True except in special situations which require doing
               the hash outside (e.g. handling Bitcoin bugs).

        Returns:
            bool: True if the signature is verified, False otherwise.
        """
        raise NotImplementedError

    def _nonce_random(self):
        return random.SystemRandom().randrange(1, self.n - 1)

    def _nonce_rfc6979(self, private_key, message):
        """ Computes a deterministic nonce (k) for use when signing
            according to RFC6979 (https://tools.ietf.org/html/rfc6979),
            Section 3.2.

        Args:
            private_key (int): The private key.
            message (bytes): A hash of the input message.

        Returns:
            int: A deterministic nonce.
        """
        hash_bytes = 32
        x = private_key.to_bytes(hash_bytes, 'big')
        # Message should already be hashed by the time it gets here,
        # so don't bother doing another hash.
        x_msg = x + message

        # Step b
        V = bytes([0x1] * hash_bytes)

        # Step c
        K = bytes([0x0] * hash_bytes)

        # Step d
        K = hmac.new(K, V + bytes([0]) + x_msg, self.hash_function).digest()

        # Step e
        V = hmac.new(K, V, self.hash_function).digest()

        # Step f
        K = hmac.new(K, V + bytes([0x1]) + x_msg, self.hash_function).digest()

        # Step g
        V = hmac.new(K, V, self.hash_function).digest()

        while True:
            # Step h.1
            T = bytes()

            # Step h.2
            while 8 * len(T) < self.nlen:
                V = hmac.new(K, V, self.hash_function).digest()
                T += V

            # Step h.3
            k = int.from_bytes(T, 'big')
            if k >= 1 and k < (self.n - 1):
                return k

            K = hmac.new(K, V + bytes([0]), self.hash_function).digest()
            V = hmac.new(K, V, self.hash_function).digest()
