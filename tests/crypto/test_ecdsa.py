import hashlib
import pytest
import random

from two1.crypto.ecdsa_base import Point
from two1.crypto import ecdsa_openssl
from two1.crypto import ecdsa_python


def make_low_s(curve, p, rec_id):
    new_p = p
    if p.y >= (curve.n // 2):
        new_p = Point(p.x, curve.n - p.y)
        rec_id ^= 0x1

    return new_p, rec_id


@pytest.mark.parametrize("curve,point_type", [
    (ecdsa_python.p256(), 'affine'),
    (ecdsa_python.p256(), 'jacobian'),
    (ecdsa_python.secp256k1(), 'affine'),
    (ecdsa_python.secp256k1(), 'jacobian')
])
def test_ecpoint(curve, point_type):
    # Test to see if n * G = point at infinity
    if point_type == 'affine':
        base_point = ecdsa_python.ECPointAffine(curve, curve.Gx, curve.Gy)
    elif point_type == 'jacobian':
        base_point = ecdsa_python.ECPointJacobian(curve, curve.Gx, curve.Gy, 1)
    else:
        print("Unsupported point_type %s!" % (point_type))

    res = base_point * curve.n
    assert res.infinity

    # Next part is a suggestion from:
    # http://crypto.stackexchange.com/a/787
    for i in range(100):
        a = random.randrange(1, curve.n)
        b = random.randrange(1, curve.n)
        c = (a + b) % curve.n

        P = base_point * a
        Q = base_point * b
        R = base_point * c

        P_plus_Q = P + Q
        Q_plus_P = Q + P

        # Jacobian coordinates are not unique (i.e. for every Z != 0
        # there is a different X, Y but when converted to affine yield
        # the same X', Y'), so we should convert to affine before
        # asserting
        if point_type == 'jacobian':
            P = P.to_affine()
            Q = Q.to_affine()
            R = R.to_affine()
            P_plus_Q = P_plus_Q.to_affine()
            Q_plus_P = Q_plus_P.to_affine()

        try:
            assert P_plus_Q == Q_plus_P
            assert P_plus_Q == R
            assert Q_plus_P == R
        except AssertionError:
            print("a        = %d" % (a))
            print("b        = %d" % (b))
            print("c        = %d" % (c))
            print("P        = %s" % (P))
            print("Q        = %s" % (Q))
            print("R        = %s" % (R))
            print("P_plus_Q = %s" % (P_plus_Q))
            print("Q_plus_P = %s" % (Q_plus_P))

            return False

    return True


@pytest.mark.parametrize("curve", [
    ecdsa_python.p256(),
    ecdsa_openssl.p256()
    ])
def test_p256(curve):
    point_class = None
    if isinstance(curve, ecdsa_python.p256):
        point_class = ecdsa_python.ECPointAffine
        # Test the basic operations, test vectors taken from:
        # https://www.nsa.gov/ia/_files/nist-routines.pdf, Section 4.3
        S = ecdsa_python.ECPointJacobian(curve,
                                         0xde2444bebc8d36e682edd27e0f271508617519b3221a8fa0b77cab3989da97c9,
                                         0xc093ae7ff36e5380fc01a5aad1e66659702de80f53cec576b6350b243042a256,
                                         1)
        T = ecdsa_python.ECPointJacobian(curve,
                                         0x55a8b00f8da1d44e62f6b3b25316212e39540dc861c89575bb8cf92e35e0986b,
                                         0x5421c3209c2d6c704835d82ac4c3dd90f61a8a52598b9e7ab656e9d8c8b24316,
                                         1)

        # Addition
        R = (S + T).to_affine()
        assert R.x == 0x72b13dd4354b6b81745195e98cc5ba6970349191ac476bd4553cf35a545a067e
        assert R.y == 0x8d585cbb2e1327d75241a8a122d7620dc33b13315aa5c9d46d013011744ac264

        # Subtraction
        R = (S - T).to_affine()
        assert R.x == 0xc09ce680b251bb1d2aad1dbf6129deab837419f8f1c73ea13e7dc64ad6be6021
        assert R.y == 0x1a815bf700bd88336b2f9bad4edab1723414a022fdf6c3f4ce30675fb1975ef3

        # Point doubling
        R = (S.double()).to_affine()
        assert R.x == 0x7669e6901606ee3ba1a8eef1e0024c33df6c22f3b17481b82a860ffcdb6127b0
        assert R.y == 0xfa878162187a54f6c39f6ee0072f33de389ef3eecd03023de10ca2c1db61d0c7

        # Scalar multiplication
        d = 0xc51e4753afdec1e6b6c6a5b992f43f8dd0c7a8933072708b6522468b2ffb06fd
        R = (S * d).to_affine()
        assert R.x == 0x51d08d5f2d4278882946d88d83c97d11e62becc3cfc18bedacc89ba34eeca03f
        assert R.y == 0x75ee68eb8bf626aa5b673ab51f6e744e06f8fcf8a6c0cf3035beca956a7b41d5

        # Joint scalar multiplicaton
        e = 0xd37f628ece72a462f0145cbefe3f0b355ee8332d37acdd83a358016aea029db7
        R = (S * d + T * e).to_affine()
        assert R.x == 0xd867b4679221009234939221b8046245efcf58413daacbeff857b8588341f6b8
        assert R.y == 0xf2504055c03cede12d22720dad69c745106b6607ec7e50dd35d54bd80f615275
    else:
        point_class = ecdsa_openssl.ECPointAffine

    # First test nonce generation according to rfc6979
    private_key = 0xC9AFA9D845BA75166B5C215767B1D6934E50C3DB36E89B127B8A622B120F6721
    public_key_x = 0x60FED4BA255A9D31C961EB74C6356D68C049B8923B61FA6CE669622E60F29FB6
    public_key_y = 0x7903FE1008B8BC99A41AE9E95628BC64F2F1B20C2D7E9F5177A3C294D4462299

    pub_key = curve.public_key(private_key)
    assert pub_key.x == public_key_x
    assert pub_key.y == public_key_y

    message = b'sample'
    k = curve._nonce_rfc6979(private_key, hashlib.sha256(message).digest())

    assert k == 0xA6E3C57DD01ABE90086538398355DD4C3B17AA873382B0F24D6129493D8AAD60

    sig_pt, _ = curve.sign(message, private_key)

    curve.y_from_x(sig_pt.x)
    assert sig_pt.x == 0xEFD48B2AACB6A8FD1140DD9CD45E81D69D2C877B56AAF991C34D0EA84EAF3716
    assert sig_pt.y == 0xF7CB1C942D657C41D436C7A1B6E29F65F3E900DBB9AFF4064DC4AB2F843ACDA8

    keys = curve.recover_public_key(message, sig_pt)
    assert len(keys) > 0
    matching_keys = 0
    for k, recid in keys:
        if k is not None and k.x == public_key_x and k.y == public_key_y:
            matching_keys += 1
    assert matching_keys > 0

    assert curve.verify(message, sig_pt, point_class(curve, public_key_x, public_key_y))

    # Taken from https://www.nsa.gov/ia/_files/ecdsa.pdf Appendix D.1.1
    private_key = 0x70a12c2db16845ed56ff68cfc21a472b3f04d7d6851bf6349f2d7d5b3452b38a
    public_key_x = 0x8101ece47464a6ead70cf69a6e2bd3d88691a3262d22cba4f7635eaff26680a8
    public_key_y = 0xd8a12ba61d599235f67d9cb4d58f1783d3ca43e78f0a5abaa624079936c0c3a9

    pub_key = curve.public_key(private_key)
    assert pub_key.x == public_key_x
    assert pub_key.y == public_key_y

    k = 0x580ec00d856434334cef3f71ecaed4965b12ae37fa47055b1965c7b134ee45d0
    modinv_k = 0x6a664fa115356d33f16331b54c4e7ce967965386c7dcbf2904604d0c132b4a74

    if isinstance(curve, ecdsa_python.p256):
        # Test modular inverse (for signing)
        assert curve.modinv(k, curve.n) == modinv_k

    message = b'This is only a test message. It is 48 bytes long'
    sig_pt, _ = curve._sign(message, private_key, True, k)

    assert sig_pt.x == 0x7214bc9647160bbd39ff2f80533f5dc6ddd70ddf86bb815661e805d5d4e6f27c
    assert sig_pt.y == 0x7d1ff961980f961bdaa3233b6209f4013317d3e3f9e1493592dbeaa1af2bc367

    assert curve.verify(message, sig_pt, point_class(curve, public_key_x, public_key_y))


@pytest.mark.parametrize("curve", [
    ecdsa_python.secp256k1(),
    ecdsa_openssl.secp256k1()
    ])
def test_secp256k1(curve):
    # Don't test point operations for OpenSSL
    if isinstance(curve, ecdsa_python.secp256k1):
        private_key, pub_key_aff = curve.gen_key_pair()

        pub_key_jac = ecdsa_python.ECPointJacobian.from_affine(pub_key_aff)
        pub_key_jac_2 = pub_key_jac * 2
        pub_key_aff_2 = pub_key_aff * 2

        assert pub_key_jac_2.to_affine() == pub_key_aff_2

        pub_key_aff_3 = pub_key_aff_2 + pub_key_aff
        pub_key_jac_3 = pub_key_jac_2 + pub_key_jac

        assert pub_key_jac_3.to_affine() == pub_key_aff_3

        k = 0xAA5E28D6A97A2479A65527F7290311A3624D4CC0FA1578598EE3C2613BF99522
        kG = (curve.base_point * k).to_affine()
        assert kG.x == 0x34F9460F0E4F08393D192B3C5133A6BA099AA0AD9FD54EBCCFACDFA239FF49C6
        assert kG.y == 0x0B71EA9BD730FD8923F6D25A7A91E7DD7728A960686CB5A901BB419E0F2CA232

        k = 0x7E2B897B8CEBC6361663AD410835639826D590F393D90A9538881735256DFAE3
        kG = (curve.base_point * k).to_affine()
        assert kG.x == 0xD74BF844B0862475103D96A611CF2D898447E288D34B360BC885CB8CE7C00575
        assert kG.y == 0x131C670D414C4546B88AC3FF664611B1C38CEB1C21D76369D7A7A0969D61D97D

        k = 0x6461E6DF0FE7DFD05329F41BF771B86578143D4DD1F7866FB4CA7E97C5FA945D
        kG = (curve.base_point * k).to_affine()
        assert kG.x == 0xE8AECC370AEDD953483719A116711963CE201AC3EB21D3F3257BB48668C6A72F
        assert kG.y == 0xC25CAF2F0EBA1DDB2F0F3F47866299EF907867B7D27E95B3873BF98397B24EE1

        k = 0x376A3A2CDCD12581EFFF13EE4AD44C4044B8A0524C42422A7E1E181E4DEECCEC
        kG = (curve.base_point * k).to_affine()
        assert kG.x == 0x14890E61FCD4B0BD92E5B36C81372CA6FED471EF3AA60A3E415EE4FE987DABA1
        assert kG.y == 0x297B858D9F752AB42D3BCA67EE0EB6DCD1C2B7B0DBE23397E66ADC272263F982

        k = 0x1B22644A7BE026548810C378D0B2994EEFA6D2B9881803CB02CEFF865287D1B9
        kG = (curve.base_point * k).to_affine()
        assert kG.x == 0xF73C65EAD01C5126F28F442D087689BFA08E12763E0CEC1D35B01751FD735ED3
        assert kG.y == 0xF449A8376906482A84ED01479BD18882B919C140D638307F0C0934BA12590BDE

    # test getting y from x
    x = 0x79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798
    y1, y2 = curve.y_from_x(x)

    assert y1 == 0x483ada7726a3c4655da4fbfc0e1108a8fd17b448a68554199c47d08ffb10d4b8

    # test the nonce generation, these test-vectors are taken from:
    # https://bitcointalk.org/index.php?topic=285142.25
    private_key = 0x1
    message = b"Satoshi Nakamoto"
    k = curve._nonce_rfc6979(private_key, hashlib.sha256(message).digest())

    assert k == 0x8F8A276C19F4149656B280621E358CCE24F5F52542772691EE69063B74F15D15

    sig_pt, rec_id = curve.sign(message, private_key)
    sig_pt, _ = make_low_s(curve, sig_pt, rec_id)
    sig_full = (sig_pt.x << curve.nlen) + sig_pt.y

    assert sig_full == 0x934b1ea10a4b3c1757e2b0c017d0b6143ce3c9a7e6a4a49860d7a6ab210ee3d82442ce9d2b916064108014783e923ec36b49743e2ffa1c4496f01a512aafd9e5  # nopep8

    private_key = 0x1
    message = b"All those moments will be lost in time, like tears in rain. Time to die..."
    k = curve._nonce_rfc6979(private_key, hashlib.sha256(message).digest())

    assert k == 0x38AA22D72376B4DBC472E06C3BA403EE0A394DA63FC58D88686C611ABA98D6B3

    sig_pt, rec_id = curve.sign(message, private_key)
    sig_pt, _ = make_low_s(curve, sig_pt, rec_id)
    sig_full = (sig_pt.x << curve.nlen) + sig_pt.y

    assert sig_full == 0x8600dbd41e348fe5c9465ab92d23e3db8b98b873beecd930736488696438cb6b547fe64427496db33bf66019dacbf0039c04199abb0122918601db38a72cfc21  # nopep8

    private_key = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364140
    message = b"Satoshi Nakamoto"
    k = curve._nonce_rfc6979(private_key, hashlib.sha256(message).digest())

    assert k == 0x33A19B60E25FB6F4435AF53A3D42D493644827367E6453928554F43E49AA6F90

    sig_pt, _ = curve.sign(message, private_key)
    sig_pt, rec_id = make_low_s(curve, sig_pt, rec_id)
    sig_full = (sig_pt.x << curve.nlen) + sig_pt.y

    assert sig_full == 0xfd567d121db66e382991534ada77a6bd3106f0a1098c231e47993447cd6af2d06b39cd0eb1bc8603e159ef5c20a5c8ad685a45b06ce9bebed3f153d10d93bed5  # nopep8

    private_key = 0xf8b8af8ce3c7cca5e300d33939540c10d45ce001b8f252bfbc57ba0342904181
    message = b"Alan Turing"
    k = curve._nonce_rfc6979(private_key, hashlib.sha256(message).digest())

    assert k == 0x525A82B70E67874398067543FD84C83D30C175FDC45FDEEE082FE13B1D7CFDF1

    sig_pt, rec_id = curve.sign(message, private_key)
    sig_pt, _ = make_low_s(curve, sig_pt, rec_id)
    sig_full = (sig_pt.x << curve.nlen) + sig_pt.y

    assert sig_full == 0x7063ae83e7f62bbb171798131b4a0564b956930092b33b07b395615d9ec7e15c58dfcc1e00a35e1572f366ffe34ba0fc47db1e7189759b9fb233c5b05ab388ea  # nopep8

    private_key = 0xe91671c46231f833a6406ccbea0e3e392c76c167bac1cb013f6f1013980455c2
    message = b"There is a computer disease that anybody who works with computers knows about. It's a very serious disease and it interferes completely with the work. The trouble with computers is that you 'play' with them!"  # nopep8
    k = curve._nonce_rfc6979(private_key, hashlib.sha256(message).digest())

    assert k == 0x1F4B84C23A86A221D233F2521BE018D9318639D5B8BBD6374A8A59232D16AD3D

    sig_pt, rec_id = curve.sign(message, private_key)
    sig_pt, _ = make_low_s(curve, sig_pt, rec_id)
    sig_full = (sig_pt.x << curve.nlen) + sig_pt.y

    assert sig_full == 0xb552edd27580141f3b2a5463048cb7cd3e047b97c9f98076c32dbdf85a68718b279fa72dd19bfae05577e06c7c0c1900c371fcd5893f7e1d56a37d30174671f6  # nopep8
