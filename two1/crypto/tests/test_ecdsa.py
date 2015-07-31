import random

from two1.crypto.ecdsa import ECPointAffine, ECPointJacobian, EllipticCurve, secp256k1

bitcoin_curve = secp256k1()

def test_ecpoint(point_type):
    # Test to see if n * G = point at infinity
    if point_type == 'affine':
        base_point = ECPointAffine(bitcoin_curve, secp256k1.Gx, secp256k1.Gy)
    elif point_type == 'jacobian':
        base_point = ECPointJacobian(bitcoin_curve, secp256k1.Gx, secp256k1.Gy, 1)
    else:
        print("Unsupported point_type %s!" % (point_type))
        
    res = base_point * bitcoin_curve.n
    assert res.infinity

    # Next part is a suggestion from:
    # http://crypto.stackexchange.com/a/787
    for i in range(100):
        a = random.randrange(1, bitcoin_curve.n)
        b = random.randrange(1, bitcoin_curve.n)
        c = (a + b) % bitcoin_curve.n

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

def test_ecdsa():
    private_key, public_key_int = bitcoin_curve.gen_key_pair()

    pub_key_aff = ECPointAffine.from_int(bitcoin_curve, public_key_int)

    pub_key_jac = ECPointJacobian.from_affine(pub_key_aff)
    pub_key_jac_2 = pub_key_jac * 2
    pub_key_aff_2 = pub_key_aff * 2

    assert pub_key_jac_2.to_affine() == pub_key_aff_2
    
    pub_key_aff_3 = pub_key_aff_2 + pub_key_aff
    pub_key_jac_3 = pub_key_jac_2 + pub_key_jac

    assert pub_key_jac_3.to_affine() == pub_key_aff_3

    k = 0xAA5E28D6A97A2479A65527F7290311A3624D4CC0FA1578598EE3C2613BF99522
    kG = (bitcoin_curve.base_point * k).to_affine()
    assert kG.x == 0x34F9460F0E4F08393D192B3C5133A6BA099AA0AD9FD54EBCCFACDFA239FF49C6
    assert kG.y == 0x0B71EA9BD730FD8923F6D25A7A91E7DD7728A960686CB5A901BB419E0F2CA232

    k = 0x7E2B897B8CEBC6361663AD410835639826D590F393D90A9538881735256DFAE3
    kG = (bitcoin_curve.base_point * k).to_affine()
    assert kG.x == 0xD74BF844B0862475103D96A611CF2D898447E288D34B360BC885CB8CE7C00575
    assert kG.y == 0x131C670D414C4546B88AC3FF664611B1C38CEB1C21D76369D7A7A0969D61D97D

    k = 0x6461E6DF0FE7DFD05329F41BF771B86578143D4DD1F7866FB4CA7E97C5FA945D
    kG = (bitcoin_curve.base_point * k).to_affine()
    assert kG.x == 0xE8AECC370AEDD953483719A116711963CE201AC3EB21D3F3257BB48668C6A72F
    assert kG.y == 0xC25CAF2F0EBA1DDB2F0F3F47866299EF907867B7D27E95B3873BF98397B24EE1

    k = 0x376A3A2CDCD12581EFFF13EE4AD44C4044B8A0524C42422A7E1E181E4DEECCEC
    kG = (bitcoin_curve.base_point * k).to_affine()
    assert kG.x == 0x14890E61FCD4B0BD92E5B36C81372CA6FED471EF3AA60A3E415EE4FE987DABA1
    assert kG.y == 0x297B858D9F752AB42D3BCA67EE0EB6DCD1C2B7B0DBE23397E66ADC272263F982

    k = 0x1B22644A7BE026548810C378D0B2994EEFA6D2B9881803CB02CEFF865287D1B9
    kG = (bitcoin_curve.base_point * k).to_affine()
    assert kG.x == 0xF73C65EAD01C5126F28F442D087689BFA08E12763E0CEC1D35B01751FD735ED3
    assert kG.y == 0xF449A8376906482A84ED01479BD18882B919C140D638307F0C0934BA12590BDE
    
if __name__ == "__main__":
    test_ecpoint('affine')
    test_ecpoint('jacobian')
    test_ecdsa()


