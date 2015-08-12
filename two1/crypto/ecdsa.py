import codecs
import hashlib
import hmac
import math
import random

from collections import namedtuple

## Links
# https://en.wikibooks.org/wiki/Cryptography/Elliptic_curve
# https://en.bitcoin.it/wiki/Secp256k1
# https://en.wikipedia.org/wiki/Elliptic_Curve_Digital_Signature_Algorithm
# http://www.coindesk.com/math-behind-bitcoin/
# https://bitcointalk.org/index.php?topic=289795.120

''' This module is intended to provide straight-forward ECDSA capability
    in a pure Python module. It provides group addition and multiplication
    using either Affine or Jacobian coordinates and makes use of constant-
    time operations to prevent against (simple) side-channel attacks.

    It does not make use of blinding techniques, prevent against certain
    kinds of cache attacks, differential side-channel attacks, etc. For those
    requiring a more secure implementation, use: https://github.com/dstufft/pynacl.
'''

Point = namedtuple('Point', ['x', 'y'])

def montgomery_ladder(k, p):
    ''' Implements scalar multiplication via the Montgomery ladder technique.
        
        This technique is used to prevent against simple side-channel attacks
        as well as certain kinds of cache attacks.

    Args:
        k (Bignum): The scalar to multiply by.
        p (ECPoint): The point to multiply by k.

    Returns:
        r[0] (ECPoint): p * k
    '''
    if isinstance(p, ECPointAffine):
        r0 = ECPointAffine(p.curve, 0, 0, True)
    elif isinstance(p, ECPointJacobian):
        r0 = ECPointJacobian(p.curve, 0, 0, 0, True)
    else:
        raise ValueError("p is not an ECPoint!")
    
    r = [r0, p]

    # Use only arithmetic operations to decide which result goes
    # where. Using branches (if/else) can lead to M-fault and cache
    # flush+reload attacks.
    for i in reversed(range(k.bit_length())):
        di = (k >> i) & 0x1
        r[(di + 1) % 2] = r[0] + r[1]
        r[di] = r[di].double()

    return r[0]


class ECPoint(object):
    ''' Base class for any elliptic curve point implementations.

        Currently there are two implementations provided: 1) ECPointAffine
        which is the standard affine coordinate system, and 2) ECPointJacobian
        which is a 3-dimensional projected coordinate system.
 
        The EllipticCurve class currently utilizes ECPointJacobian for efficiency
        reasons. However, switching to the affine implementation is trivial.

    Args:
        curve (EllipticCurve): The curve the point is on.
        x (Bignum): x component of point.
        y (Bignum): y component of point.
        z (Bignum) (Optional): z component of point (only used in Jacobian)
        infinity (bool) (Optional): Whether this is the point-at-infinity.

    Returns:
        p (ECPoint): the point formed by (x, y, z) on curve.
    '''
    def __init__(self, curve, x, y, z=0, infinity=False):
        self.x = x
        self.y = y
        self.z = z
        self.curve = curve
        self.infinity = infinity
        
    def __str__(self):
        raise NotImplementedError()

    def __eq__(self, b):
        return ((self.x == b.x) and (self.y == b.y) and (self.z == b.z)) or (self.infinity and b.infinity)

    def __add__(self, b):
        raise NotImplementedError()

    def __sub__(self, b):
        raise NotImplementedError()
    
    def __mul__(self, k):
        raise NotImplementedError()

    def double(self):
        ''' Implements a doubling of this point (i.e. 2P)
        '''
        raise NotImplementedError()

    def to_affine(self):
        ''' If not affine, converts to affine. Otherwise should return `self`.
        '''
        raise NotImplementedError()

    def to_jacobian(self):
        ''' If not affine, converts to affine. Otherwise should return `self`.
        '''
        raise NotImplementedError()


class ECPointJacobian(ECPoint):
    ''' Encapsulates a point on an elliptic curve.

        This class provides a Jacobian representation of a point
        on an elliptic curve. It presents the standard addition and
        scalar multiplication operations between two points as overloaded
        '+' and '*' Python operators. Scalar multiplications are computed
        via the Montgomery Ladder technique (same as OpenSSL).

        All math operations from:
        https://en.wikibooks.org/wiki/Cryptography/Prime_Curve/Jacobian_Coordinates
    
    Args:
        curve (EllipticCurve): The curve the point is on.
        x (Bignum): x component of point.
        y (Bignum): y component of point.
        z (Bignum): z component of point.
        infinity (bool) (Optional): Whether this is the point-at-infinity.

    Returns:
        p (ECPointAffine): the point formed by (x, y) on curve.
    '''

    @staticmethod
    def from_affine(affine_point):
        ''' Converts from an affine point to a Jacobian representation.
            This is simplisticly done by using `Z = 1`.
        
        Args:
            affine_point (ECPointAffine): The affine point to convert.

        Returns:
            jacobian_point (ECPointJacobian): The jacobian representation.
        '''
        return affine_point.to_jacobian()

    @staticmethod
    def from_jacobian(jacobian_point):
        ''' A no-op since the point is already jacobian.

        Args:
            jacobian_point (ECPointJacobian): A Jacobian point

        Returns:
            jacobian_point (ECPointJacobian): Returns the input arg.
        '''
        return jacobian_point

    @staticmethod
    def from_int(cls, curve, i):
        ''' Creates a point from an integer.
        
            Assumes that pt.y is the lower bits of i and pt.x is
            the upper bits of i.
        
        Args:
            curve (EllipticCurve): The curve to which the point belongs.
            i (Bignum): integer representing the point.

        Returns:
            p (ECPointJacobian): point on curve.
        '''
        return ECPointAffine.from_int(curve, i).to_jacobian()
    
    def __init__(self, curve, x, y, z, infinity=False):
        super().__init__(curve, x, y, z, infinity)

    def __str__(self):
        return "O" if self.infinity else "(%d, %d, %d)" % (self.x, self.y, self.z)

    def __add__(self, b):
        assert self.curve == b.curve

        if self.infinity:
            return b
        if b.infinity:
            return self
        
        u1 = (self.x * pow(b.z, 2, self.curve.p)) % self.curve.p
        u2 = (b.x * pow(self.z, 2, self.curve.p)) % self.curve.p
        s1 = (self.y * pow(b.z, 3, self.curve.p)) % self.curve.p
        s2 = (b.y * pow(self.z, 3, self.curve.p)) % self.curve.p

        if u1 == u2:
            if s1 != s2:
                return ECPointJacobian(self.curve, 0, 0, 0, True)
            else:
                return self.double()

        h = u2 - u1
        r = s2 - s1

        h2 = pow(h, 2, self.curve.p)
        h3 = pow(h, 3, self.curve.p)

        x3 = (pow(r, 2, self.curve.p) - h3 - (2 * u1 * h2)) % self.curve.p
        y3 = (r * (u1 * h2 - x3) - (s1 * h3)) % self.curve.p
        z3 = (self.z * b.z * h) % self.curve.p

        return ECPointJacobian(self.curve, x3, y3, z3)

    def __sub__(self, b):
        assert b.curve == self.curve
        # b.curve.p - b.y is effectively -b.y % b.curve.p
        return self + ECPointJacobian(b.curve, b.x, b.curve.p - b.y, b.z)

    def __mul__(self, k):
        return montgomery_ladder(k, ECPointJacobian(self.curve, self.x, self.y, self.z))
    
    def double(self):
        ''' Optimized point doubling operation that results in `2*self`.

        Returns:
            p2 (ECPointJacobian): The point corresponding to `2*self`.
        '''
        if self.y == 0:
            return ECPointJacobian(self.curve, 0, 0, 0, True)
        
        s = (4 * self.x * pow(self.y, 2, self.curve.p)) % self.curve.p
        m = (3 * pow(self.x, 2, self.curve.p) + self.curve.a * pow(self.z, 4, self.curve.p)) % self.curve.p

        x = (pow(m, 2, self.curve.p) - 2 * s) % self.curve.p
        y = (m * (s - x) - 8 * pow(self.y, 4, self.curve.p)) % self.curve.p
        z = (2 * self.y * self.z) % self.curve.p

        return ECPointJacobian(self.curve, x, y, z)

    def to_affine(self):
        ''' Converts this point to an affine representation.

        Returns:
            p (ECPointAffine): The affine representation.
        '''
        if self.z == 1:
            return ECPointAffine(self.curve, self.x, self.y)

        try:
            x = (self.x * self.curve.modinv(pow(self.z, 2, self.curve.p), self.curve.p)) % self.curve.p
            y = (self.y * self.curve.modinv(pow(self.z, 3, self.curve.p), self.curve.p)) % self.curve.p
        except ValueError:
            return ECPointAffine(self.curve, 0, 0, True)

        return ECPointAffine(self.curve, x, y)

    def to_jacobian(self):
        ''' No-op since this is already a Jacobian point.

        Returns:
            self (ECPointJacobian): Just returns this point.
        '''
        return self
    
class ECPointAffine(ECPoint):
    ''' Encapsulates a point on an elliptic curve.

        This class provides an affine representation of a point
        on an elliptic curve. It presents the standard addition and
        scalar multiplication operations between two points as overloaded
        '+' and '*' Python operators. Scalar multiplications are computed
        via the Montgomery Ladder technique (same as OpenSSL).

    Note:
        This makes use of constant-time operations but is not safe from
        FLUSH+RELOAD cache attacks: http://eprint.iacr.org/2014/140.pdf.

    Args:
        curve (EllipticCurve): The curve the point is on.
        x (Bignum): x component of point.
        y (Bignum): y component of point.

    Returns:
        p (ECPointAffine): the point formed by (x, y) on curve.
    '''

    @staticmethod
    def from_affine(affine_point):
        ''' A no-op since the point is already affine.

        Args:
            affine_point (ECPointAffine): A Affine point

        Returns:
            affine_point (ECPointAffine): Returns the input arg.
        '''
        return affine_point

    @staticmethod
    def from_jacobian(jacobian_point):
        ''' Converts from a Jacobian point to an affine representation.
        
        Args:
            jacobian_point (ECPointJacobian): The Jacobian point to convert.

        Returns:
            affine_point (ECPointAffine): The affine representation.
        '''
        return jacobian_point.to_affine()
    
    @classmethod
    def from_int(cls, curve, i):
        ''' Creates a point from an integer.
        
            Assumes that pt.y is the lower bits of i and pt.x is
            the upper bits of i.
        
        Args:
            curve (EllipticCurve): The curve to which the point belongs.
            i (Bignum): integer representing the point.

        Returns:
            p (ECPointAffine): point on curve.
        '''
        x = i >> curve.nlen
        y = i & (2 ** curve.nlen - 1)

        assert curve.is_on_curve(Point(x, y))

        return ECPointAffine(curve, x, y)

    def __init__(self, curve, x, y, infinity=False):
        super().__init__(curve, x, y, 0, infinity)

    def __str__(self):
        return "O" if self.infinity else "(%032x, %032x)" % (self.x, self.y)

    def __add__(self, b):
        assert b.curve == self.curve
        
        ## See https://www.certicom.com/index.php/32-arithmetic-in-an-elliptic-curve-group-over-fp
        if self.infinity:
            return b
        if b.infinity:
            return self
        if self == b:
            return self.double()

        if (self.x == b.x) and ((self.y != b.y) or (self.y == 0 and b.y == 0)):
            return ECPointAffine(self.curve, 0, 0, True)
        
        s = self._slope(b)
        xr = (s ** 2 - self.x - b.x) % self.curve.p
        yr = (-self.y + s * (self.x - xr)) % self.curve.p

        assert self.curve.is_on_curve(Point(xr, yr))
        
        return ECPointAffine(self.curve, xr, yr)

    def __sub__(self, b):
        assert b.curve == self.curve
        return self + ECPointAffine(b.curve, b.x, b.curve.p - b.y)

    def __mul__(self, k):
        return montgomery_ladder(k, ECPointAffine(self.curve, self.x, self.y))
    
    def _slope(self, q):
        ''' Determines the slope between this point and another
            on this point's curve.
        
        Args:
            q (ECPointAffine): Second point

        Returns:
            s (int): Slope between self and q.
        '''
        n = self.y - q.y
        d = self.x - q.x
        d_modinv = EllipticCurve.modinv(d, self.curve.p)
        return (n * d_modinv) % self.curve.p
    
    def double(self):
        ''' Doubles this point.

        Returns:
            2p (ECPointAffine): The point corresponding to 2*self.
        '''
        if self.infinity:
            return self
        
        s = ((3 * self.x ** 2 + self.curve.a) * self.curve.modinv(2 * self.y, self.curve.p)) % self.curve.p
        xr = (s ** 2 - (2 * self.x)) % self.curve.p
        yr = (-self.y + s * (self.x - xr)) % self.curve.p

        assert self.curve.is_on_curve(Point(xr, yr))
        
        return ECPointAffine(self.curve, xr, yr)

    def to_affine(self):
        ''' No-op since this is already a Affine point.
                
        Returns:
            self (ECPointAffine): Just returns this point.
        '''
        return self

    def to_jacobian(self):
        ''' Converts this point to an jacobian representation.

        Returns:
            p (ECPointJacobian): The jacobian representation.
        '''
        return ECPointJacobian(self.curve, self.x, self.y, 1, self.infinity)

    @property
    def compressed_bytes(self):
        ''' Returns the compressed bytes for this point.

            If pt.y is odd, 0x03 is pre-pended to pt.x.
            If pt.y is even, 0x02 is pre-pended to pt.x.

        Returns:
            b (bytes): Compressed byte representation.
        '''
        nbytes = math.ceil(self.curve.nlen / 8)
        return bytes([(self.y & 0x1) + 0x02]) + self.x.to_bytes(nbytes, 'big')
    
    def __bytes__(self):
        ''' Returns the full-uncompressed point
        '''
        nbytes = math.ceil(self.curve.nlen / 8)
        return bytes([0x04]) + self.x.to_bytes(nbytes, 'big') + self.y.to_bytes(nbytes, 'big')
    
class EllipticCurve:
    ''' A generic class for elliptic curves and operations on them.

        The curves must be of the form: y^2 = x^3 + a*x + b.
    
    Args:
        p (Bignum): Prime that defines the field.
        a (int): linear coefficient of the curve.
        b (int): constant of the curve.
        n (Bignum): order of G (smallest prime) such that nG = infinity.
        G (Point): generator (base point) of the curve.
    '''
    @staticmethod
    def _extended_gcd(aa, bb):
        ## https://en.wikipedia.org/wiki/Extended_Euclidean_algorithm
        lastremainder, remainder = abs(aa), abs(bb)
        x, lastx, y, lasty = 0, 1, 1, 0
        while remainder:
            lastremainder, (quotient, remainder) = remainder, divmod(lastremainder, remainder)
            x, lastx = lastx - quotient*x, x
            y, lasty = lasty - quotient*y, y
        return lastremainder, lastx * (-1 if aa < 0 else 1), lasty * (-1 if bb < 0 else 1)

    @staticmethod
    def modinv(a, n):
        ''' Provides the modular inverse of a wrt n.

            This uses the extended Euclidean algorithm to compute the
            the GCD of a, n.

        Args:
            a (Bignum): number to find modular inverse of
            n (Bignum): modulus
        '''
        ## From http://rosettacode.org/wiki/Modular_inverse#Python
        g, x, y = EllipticCurve._extended_gcd(a, n)
        if g != 1:
            raise ValueError("in EllipticCurve.modinv: g (%d) != 1, x = %d, y = %d" % (g, x, y))
        return x % n

    @staticmethod
    def modsqrt(a, n):
        if a == 0:
            return 0
        elif n == 2:
            return n
        elif n % 4 == 3:
            return pow(a, (n + 1) // 4, n)
        else:
            raise NotImplementedError("The generalized modular square root using Tonelli-Shanks hasn't been implemented yet.")

    def __init__(self, p, a, b, n, G, hash_function):
        self.a = a
        self.b = b
        self.p = p
        self.n = n
        self.G = G
        self.hash_function = hash_function

        self.nlen = self.n.bit_length()
        self.plen = self.p.bit_length()

    def __eq__(self, other_curve):
        return (self.a == other_curve.a) and (self.b == other_curve.b) and \
            (self.p == other_curve.p) and (self.n == other_curve.n) and (self.G == other_curve.G)

    def is_on_curve(self, p):
        ''' Checks whether a point is on the curve.

        Args:
            p (ECPointAffine): Point to be checked

        Returns:
            on_curve (Bool): True if p is on the curve, False otherwise.
        '''
        return (pow(p.y, 2, self.p) - pow(p.x, 3, self.p) - self.a * p.x - self.b) % self.p == 0

    @property
    def base_point(self):
        ''' Returns the base point for this curve.

        Returns:
            base (ECPointJacobian): the base point
        '''
        return ECPointJacobian(self, self.G.x, self.G.y, 1)
        
    def y_from_x(self, x):
        ''' Computes the y component corresponding to x.

            Since elliptic curves are symmetric about the x-axis,
            the x component (and sign) is all that is required to determine
            a point on the curve. Since the sign may be represented in an
            application-defined manner, this only provides the positive y
            value. It is left to the caller to apply the appropriate sign.

        Args:
            x (Bignum): x component of the point.

        Returns:
            y (Bignum): positive y component of the point.
        '''
        a = (pow(x, 3, self.p) + self.a * x + self.b) % self.p
        y1 = self.modsqrt(a, self.p)
        y2 = self.p - y1
        rv = []
        if self.is_on_curve(Point(x, y1)):
            rv.append(y1)
        if self.is_on_curve(Point(x, y2)):
            rv.append(y2)

        return rv

    def gen_key_pair(self):
        ''' Generates a public/private key pair.

        Returns:
            (private, public_full) (tuple): A private key in the range of 1 to `self.n -1`
               and a "full" public key (i.e. not compressed).
        '''
        private = random.SystemRandom().randrange(1, self.n - 1)
        return private, self.public_key(private)

    def public_key(self, private_key):
        ''' Returns the public (verifying) key for a given private key.

        Args:
            private_key (Bignum): the private key to derive the public key for.

        Returns:
            public_full (Bignum): a "full" public key represented as a single
               integer with the X (R) component as the MSBs and the Y (S) component
               as the LSBs.
        '''
        public = (self.base_point * private_key).to_affine()
        public_full = (public.x << self.nlen) + public.y

        return public_full

    def recover_public_key(self, message, signature, recovery_id=None):
        ''' Recovers possibilities for the public key associated with the
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
           rv (list(ECPointAffine)): List of points representing valid public
              keys that verify signature.
        '''
        r = signature.x
        s = signature.y

        r_modinv = self.modinv(r, self.n)

        if recovery_id is not None:
            i_list = [recovery_id >> 1]
            k_list = [recovery_id & 0x1]
        else:
            i_list = range(2)
            k_list = range(2)
        
        rv = []
        for i in i_list:
            x = (r + self.n * i) % self.p
            ys = self.y_from_x(x)
            if not ys:
                continue

            for k in k_list:
                R  = ECPointJacobian(self, r, ys[k % 2], 1)
            
                if not (R * self.n).to_affine().infinity:
                    continue

                num_bytes = math.ceil(self.nlen / 8)
                z = int.from_bytes(self.hash_function(message).digest()[:num_bytes], 'big')
        
                zG = self.base_point * z
                pub_key = ((R  * s - zG) * r_modinv).to_affine()

                rv.append((pub_key, 2 * i + k))

        return rv
    
    def _sign(self, message, private_key, do_hash=True, secret=None):
        ''' DO NOT USE THIS FUNCTION DIRECTLY. Call self.sign() instead.
        '''
        hashed = self.hash_function(message).digest() if do_hash else message
        z = int.from_bytes(hashed, 'big')
        
        G = self.base_point
        
        r = 0
        s = 0
        recovery_id = 0
        while r == 0 or s == 0:
            k = self._nonce_rfc6979(private_key, hashed) if secret is None else secret
            
            p = (G * k).to_affine()
            # This works if self.h = 1. For curves with a larger
            # co-factor (nearly none), this will be insufficient.
            recovery_id = 2 if p.x > self.n else 0
            recovery_id |= (p.y & 0x1)
            r = p.x % self.n
            if r == 0:
                continue

            sp = ((z + r * private_key) * self.modinv(k, self.n)) % self.n
            s = self._make_canonical(sp)
            if s != sp:
                recovery_id ^= 0x1

        return (Point(r, s), recovery_id)

    def sign(self, message, private_key, do_hash=True):
        ''' Signs a message with the given private key.

        Args:
            message (bytes): The message to be signed
            private_key (Bignum): Integer that is the private key
            do_hash (bool): True if the message should be hashed prior
               to signing, False if not. This should always be left as
               True except in special situations which require doing
               the hash outside (e.g. handling Bitcoin bugs).

        Returns:
            sig, recovery_id (Point, int): The point (r, s) representing the signature
               and the ID representing which public key possibility is associated
               with the private key being used to sign.
        '''
        return self._sign(message, private_key, do_hash)

    def verify(self, message, signature, public_key, do_hash=True):
        ''' Verifies that signature was generated with a private key corresponding
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
            b (Bool): True if the signature is verified, False otherwise.
        '''
        r = signature.x
        s = signature.y

        hashed = self.hash_function(message).digest() if do_hash else message
        z = int.from_bytes(hashed, 'big')

        G = self.base_point

        assert public_key.x >= 1 and public_key.x <= (self.n - 1)
        assert public_key.y >= 1 and public_key.y <= (self.n - 1)
        
        w = self.modinv(s, self.n)
        u = (z * w) % self.n
        
        v = (r * w) % self.n
        pt = (G * u + ECPointJacobian.from_affine(public_key) * v).to_affine()

        return r == (pt.x % self.n)

    def _make_canonical(self, s):
        return s

    def _nonce_random(self):
        return random.SystemRandom().randrange(1, self.n - 1)
    
    def _nonce_rfc6979(self, private_key, message):
        """ Computes a deterministic nonce (k) for use when signing
            according to RFC6979 (https://tools.ietf.org/html/rfc6979),
            Section 3.2.

        Args:
            private_key (Bignum): The private key.
            message (bytes): A hash of the input message.

        Returns:
            k (Bignum): A deterministic nonce.
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

        # Step h.1
        T = bytes()

        # Step h.2
        while len(T) < (self.nlen / 8):
            V = hmac.new(K, V, self.hash_function).digest()
            T += V
            k = int.from_bytes(T, 'big')
            if k >= 1 and k < (self.n - 1):
                return k
            else:
                K = hmac.new(K, V + bytes([0]), self.hash_function).digest()
                V = hmac.new(K, V, self.hash_function).digest()

    
class p256(EllipticCurve):
    ''' P-256 NIST-defined curve
    '''
    P  = 0xffffffff00000001000000000000000000000000ffffffffffffffffffffffff
    A  = 0xffffffff00000001000000000000000000000000fffffffffffffffffffffffc
    B  = 0x5ac635d8aa3a93e7b3ebbd55769886bc651d06b0cc53b0f63bce3c3e27d2604b
    N  = 0xffffffff00000000ffffffffffffffffbce6faada7179e84f3b9cac2fc632551
    Gx = 0x6b17d1f2e12c4247f8bce6e563a440f277037d812deb33a0f4a13945d898c296
    Gy = 0x4fe342e2fe1a7f9b8ee7eb4a7c0f9e162bce33576b315ececbb6406837bf51f5

    def __init__(self):
        EllipticCurve.__init__(
            self,
            p256.P,
            p256.A,
            p256.B,
            p256.N,
            Point(p256.Gx, p256.Gy),
            hashlib.sha256
        )

        
class secp256k1(EllipticCurve):
    ''' Elliptic curve used in Bitcoin.
    '''
    P  = 2 ** 256 - 2 ** 32 - 977
    A  = 0
    B  = 7
    N  = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
    Gx = 0x79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798
    Gy = 0x483ada7726a3c4655da4fbfc0e1108a8fd17b448a68554199c47d08ffb10d4b8
            
    def __init__(self):
        EllipticCurve.__init__(
            self,
            secp256k1.P,
            secp256k1.A,
            secp256k1.B,
            secp256k1.N,
            Point(secp256k1.Gx, secp256k1.Gy),
            hashlib.sha256
        )

    def _make_canonical(self, s):
        # Bitcoin deals with large s, by subtracting
        # s from the curve order. See:
        # https://bitcointalk.org/index.php?topic=285142.30;wap2
        if s >= (self.n // 2):
            return self.n - s
        else:
            return s
