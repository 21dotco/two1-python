import pytest

from two1.bitcoin import crypto

# Test vectors from:
# https://github.com/bitcoin/bips/blob/master/bip-0032.mediawiki#test-vectors

test_vectors = [("000102030405060708090a0b0c0d0e0f",
                 [('master',
                   "xprv9s21ZrQH143K3QTDL4LXw2F7HEK3wJUD2nW2nRk4stbPy6cq3jPPqjiChkVvvNKmPGJxWUtg6LnF5kejMRNNU3TGtRBeJgk33yuGBxrMPHi",  # nopep8
                   "xpub661MyMwAqRbcFtXgS5sYJABqqG9YLmC4Q1Rdap9gSE8NqtwybGhePY2gZ29ESFjqJoCu1Rupje8YtGqsefD265TMg7usUDFdp6W1EGMcet8"),  # nopep8
                  (0x80000000,
                   "xprv9uHRZZhk6KAJC1avXpDAp4MDc3sQKNxDiPvvkX8Br5ngLNv1TxvUxt4cV1rGL5hj6KCesnDYUhd7oWgT11eZG7XnxHrnYeSvkzY7d2bhkJ7",  # nopep8
                   "xpub68Gmy5EdvgibQVfPdqkBBCHxA5htiqg55crXYuXoQRKfDBFA1WEjWgP6LHhwBZeNK1VTsfTFUHCdrfp1bgwQ9xv5ski8PX9rL2dZXvgGDnw"),  # nopep8
                  (1,
                   "xprv9wTYmMFdV23N2TdNG573QoEsfRrWKQgWeibmLntzniatZvR9BmLnvSxqu53Kw1UmYPxLgboyZQaXwTCg8MSY3H2EU4pWcQDnRnrVA1xe8fs",  # nopep8
                   "xpub6ASuArnXKPbfEwhqN6e3mwBcDTgzisQN1wXN9BJcM47sSikHjJf3UFHKkNAWbWMiGj7Wf5uMash7SyYq527Hqck2AxYysAA7xmALppuCkwQ"),  # nopep8
                  (0x80000002,
                   "xprv9z4pot5VBttmtdRTWfWQmoH1taj2axGVzFqSb8C9xaxKymcFzXBDptWmT7FwuEzG3ryjH4ktypQSAewRiNMjANTtpgP4mLTj34bhnZX7UiM",  # nopep8
                   "xpub6D4BDPcP2GT577Vvch3R8wDkScZWzQzMMUm3PWbmWvVJrZwQY4VUNgqFJPMM3No2dFDFGTsxxpG5uJh7n7epu4trkrX7x7DogT5Uv6fcLW5"),  # nopep8
                  (2,
                   "xprvA2JDeKCSNNZky6uBCviVfJSKyQ1mDYahRjijr5idH2WwLsEd4Hsb2Tyh8RfQMuPh7f7RtyzTtdrbdqqsunu5Mm3wDvUAKRHSC34sJ7in334",  # nopep8
                   "xpub6FHa3pjLCk84BayeJxFW2SP4XRrFd1JYnxeLeU8EqN3vDfZmbqBqaGJAyiLjTAwm6ZLRQUMv1ZACTj37sR62cfN7fe5JnJ7dh8zL4fiyLHV"),  # nopep8
                  (1000000000,
                   "xprvA41z7zogVVwxVSgdKUHDy1SKmdb533PjDz7J6N6mV6uS3ze1ai8FHa8kmHScGpWmj4WggLyQjgPie1rFSruoUihUZREPSL39UNdE3BBDu76",  # nopep8
                   "xpub6H1LXWLaKsWFhvm6RVpEL9P4KfRZSW7abD2ttkWP3SSQvnyA8FSVqNTEcYFgJS2UaFcxupHiYkro49S8yGasTvXEYBVPamhGW6cFJodrTHy")]),  # nopep8
                ("fffcf9f6f3f0edeae7e4e1dedbd8d5d2cfccc9c6c3c0bdbab7b4b1aeaba8a5a29f9c999693908d8a8784817e7b7875726f6c696663605d5a5754514e4b484542",  # nopep8
                 [('master',
                   "xprv9s21ZrQH143K31xYSDQpPDxsXRTUcvj2iNHm5NUtrGiGG5e2DtALGdso3pGz6ssrdK4PFmM8NSpSBHNqPqm55Qn3LqFtT2emdEXVYsCzC2U",  # nopep8
                   "xpub661MyMwAqRbcFW31YEwpkMuc5THy2PSt5bDMsktWQcFF8syAmRUapSCGu8ED9W6oDMSgv6Zz8idoc4a6mr8BDzTJY47LJhkJ8UB7WEGuduB"),  # nopep8
                  (0,
                   "xprv9vHkqa6EV4sPZHYqZznhT2NPtPCjKuDKGY38FBWLvgaDx45zo9WQRUT3dKYnjwih2yJD9mkrocEZXo1ex8G81dwSM1fwqWpWkeS3v86pgKt",  # nopep8
                   "xpub69H7F5d8KSRgmmdJg2KhpAK8SR3DjMwAdkxj3ZuxV27CprR9LgpeyGmXUbC6wb7ERfvrnKZjXoUmmDznezpbZb7ap6r1D3tgFxHmwMkQTPH"),  # nopep8
                  (0xffffffff,
                   "xprv9wSp6B7kry3Vj9m1zSnLvN3xH8RdsPP1Mh7fAaR7aRLcQMKTR2vidYEeEg2mUCTAwCd6vnxVrcjfy2kRgVsFawNzmjuHc2YmYRmagcEPdU9",  # nopep8
                   "xpub6ASAVgeehLbnwdqV6UKMHVzgqAG8Gr6riv3Fxxpj8ksbH9ebxaEyBLZ85ySDhKiLDBrQSARLq1uNRts8RuJiHjaDMBU4Zn9h8LZNnBC5y4a"),  # nopep8
                  (1,
                   "xprv9zFnWC6h2cLgpmSA46vutJzBcfJ8yaJGg8cX1e5StJh45BBciYTRXSd25UEPVuesF9yog62tGAQtHjXajPPdbRCHuWS6T8XA2ECKADdw4Ef",  # nopep8
                   "xpub6DF8uhdarytz3FWdA8TvFSvvAh8dP3283MY7p2V4SeE2wyWmG5mg5EwVvmdMVCQcoNJxGoWaU9DCWh89LojfZ537wTfunKau47EL2dhHKon"),  # nopep8
                  (0xfffffffe,
                   "xprvA1RpRA33e1JQ7ifknakTFpgNXPmW2YvmhqLQYMmrj4xJXXWYpDPS3xz7iAxn8L39njGVyuoseXzU6rcxFLJ8HFsTjSyQbLYnMpCqE2VbFWc",  # nopep8
                   "xpub6ERApfZwUNrhLCkDtcHTcxd75RbzS1ed54G1LkBUHQVHQKqhMkhgbmJbZRkrgZw4koxb5JaHWkY4ALHY2grBGRjaDMzQLcgJvLJuZZvRcEL"),  # nopep8
                  (2,
                   "xprvA2nrNbFZABcdryreWet9Ea4LvTJcGsqrMzxHx98MMrotbir7yrKCEXw7nadnHM8Dq38EGfSh6dqA9QWTyefMLEcBYJUuekgW4BYPJcr9E7j",  # nopep8
                   "xpub6FnCn6nSzZAw5Tw7cgR9bi15UV96gLZhjDstkXXxvCLsUXBGXPdSnLFbdpq8p9HmGsApME5hQTZ3emM2rnY5agb9rXpVGyy3bdW6EEgAtqt")  # nopep8
                 ])
]


@pytest.mark.parametrize("vector", test_vectors)
def test_hdkeys(vector):
    seed = vector[0]
    checks = vector[1]

    pub_key = None
    for i in range(len(checks)):
        index = checks[i][0]

        der_pub_key = None
        if index == 'master':
            priv_key = crypto.HDPrivateKey.master_key_from_seed(seed)
        else:
            priv_key = crypto.HDPrivateKey.from_parent(priv_key, index)
            if index & 0x80000000:
                with pytest.raises(ValueError):
                    der_pub_key = crypto.HDPublicKey.from_parent(pub_key, index)
            else:
                der_pub_key = crypto.HDPublicKey.from_parent(pub_key, index)

        pub_key = priv_key.public_key

        if index == 'master':
            assert priv_key.master
        else:
            if index & 0x80000000:
                assert der_pub_key is None
                assert priv_key.hardened
                assert pub_key.hardened
            else:
                assert not priv_key.hardened
                assert not pub_key.hardened
                assert not der_pub_key.hardened
                assert der_pub_key.to_b58check() == checks[i][2]

        assert priv_key.to_b58check() == checks[i][1]
        assert pub_key.to_b58check() == checks[i][2]

        deser_priv_key = crypto.HDKey.from_b58check(checks[i][1])
        deser_pub_key = crypto.HDKey.from_b58check(checks[i][2])

        for pair in [(deser_priv_key, priv_key), (deser_pub_key, pub_key)]:
            if isinstance(pair[1], crypto.HDPrivateKey):
                assert isinstance(pair[0], crypto.HDPrivateKey)
                assert pair[0]._key.key == pair[1]._key.key
            else:
                assert isinstance(pair[0], crypto.HDPublicKey)
                assert pair[0]._key.point.x == pair[1]._key.point.x
                assert pair[0]._key.point.y == pair[1]._key.point.y

            assert pair[0].chain_code == pair[1].chain_code
            assert pair[0].index == pair[1].index
            assert pair[0].depth == pair[1].depth
            assert pair[0].parent_fingerprint == pair[1].parent_fingerprint


def test_mnemonic_key_generation():
    mnemonic = "tuna object element cancel hard nose faculty noble swear net subway offer"

    m = crypto.HDPrivateKey.master_key_from_mnemonic(mnemonic)

    assert m.to_b58check() == "xprv9s21ZrQH143K3But1Hju6Ga2H7dn9CyWz7nfAtdEWLhQZ7GGad7qKm4Btg9yfWgBW1xtfjqimL3zHe3TYQaPPXsQDNWSMinX1HdVG4axX5p"  # nopep8

    keys = crypto.HDKey.from_path(m, "m/44'/0'/0'")
    ext_chain_key = crypto.HDPrivateKey.from_parent(keys[-1], 0)
    int_chain_key = crypto.HDPrivateKey.from_parent(keys[-1], 1)

    assert int_chain_key.to_b58check() == "xprvA1fFrEZ8jPQTDp6b8qLAPJPXEDmWwCQqUq7R6vFkSDBs7SvKW3m9bCpXjD8v29Cof7zrf1QNyEHgtgPZS5AymTz1m15196CoAbnv1nGm9gB"  # nopep8
    assert int_chain_key.public_key.to_b58check() == "xpub6EecFk62ZkxkSJB4ErsAkSLFnFc1Lf8gr431uJfMzYiqzFFU3b5Q9191aWqrjJxq2kS9unmEyBCLZpm9X1dBikzJpASak5XiHfUKChD8kT2"  # nopep8

    int_addresses = ["12q2xjqTh6ZNHUTQLWSs9uSyDkGHNpQAzu",
                     "1NpksrEeUpMcbw6ekWPZfPd3qAhEL5ygJ4",
                     "1BruaiE6VNXQdeDdhGKhB1x8sq2NcJrDBX",
                     "1ECsMhxMnHR7mMjaP1yBRhUNaUszZUYQUj",
                     "1KbGXnyg1gXx4CA3YnCmpKH252jw8pR9C1",
                     "1DVfjTiL4mQMui188i615q4ybZRuT65DqS",
                     "1MhKGVuRN6jxFSLU3LNmAEu8gMwG4zWE18",
                     "1756Kxj3LRVB8cHe9yRCpppSmeRqGVXZxP",
                     "1PWMMrZM356ggUrmTTN7ZHpUb3Uic3VaPz",
                     "1GJ1nDUhyBDB2xtWPV3hXcQyii5Ao7FuGV",
                     "12Xb9HW6VijputQGYrA3PsxJZnSqf3p8rJ",
                     "1GEntRhFbgNSmnS8zZKNXsT2tGoYreSwL5",
                     "1Bn6U6YUNr46nmgro2ujqpWWDZbgquKAyq",
                     "193fqpFGNbrV83uKFA5TuFRBBpHbTZoWj5",
                     "1EyU9mFWwkHwSmAfu5QBs4FVFwwAVdyft8",
                     "13bT9WXLEpadRzj31VgoRzSB8KpHp8nk7d",
                     "1PWsee2bHn8BGbKTMMdWScQ1BtggJ2T7s3",
                     "12NCpy5sVk9ZZVLdhrH19na6nqW3Bpj4Wk",
                     "1MxSrzVmbZABSH5ei7hgNbrApngPeCPA9y",
                     "1TJqdM2Hfw8SM26NdrBT1yVbqVcXoKdBQ"]

    assert [crypto.HDPublicKey.from_parent(int_chain_key, i).address() for i in range(20)] == int_addresses

    assert ext_chain_key.to_b58check() == "xprvA1fFrEZ8jPQTA6nguZQauChJ8ubexZhRbyowy1kzi7WiAodkwWxM9w8NaCzhEWqMukV7zXwAdzRZJ5mVCwG8NmhVBkZfrjEa1aZUTnvzSDL"  # nopep8
    assert ext_chain_key.public_key.to_b58check() == "xpub6EecFk62ZkxkNasA1awbGLe2gwS9N2RGyCjYmQAcGT3h3bxuV4GbhjSrRTJBzbkmu8fMzoUDAixdHSuso7aw2BEPVfUh6R4AFJWLjps2JX6"  # nopep8

    ext_addresses = ["1Lqf8UgzG3SWWTe9ab8YPwgm6gzkJCZMX6",
                     "1KuwentNouJBjKZgfrcPidSBELyXkpvpDa",
                     "1DgSD3feEKysnre6bL2xQAUyza4cdShVX1",
                     "1JefJedKMWX4NowgGujdhr7Lq3EFHtwDjQ",
                     "1A994BxdSc5HzNeQ8vUUrZJ7X1azjvkQ9",
                     "1G2q6e5zvQuxakJmeZuTM2QVuwxXmRff2n",
                     "1DDXZK4riAhNHW2AUAKcyphFmJQy2i1V8z",
                     "16fb3HunUPcLc5sh5iiDNpbhLv9B2DQVN5",
                     "1JckLjeHzphmCxx6jyCRctkfAF4Ak5RhRZ",
                     "1FSa872pSXMF3dSaXK4BgaFsJSBSaAFuHj",
                     "1DXWGJz3aW2miZdqZzKjtriHCVLdBchVHk",
                     "1KYwjXTfWUW3SujyuwxU3fuGS2gzhkz9xY",
                     "1LYNKZSBsAUScADJ4w8KaG26CQvcKLE5sF",
                     "15U6sh5Q1QMXrHov86u8YSfnHMGSgXL8wi",
                     "19prymRW7LWk7aZeSXdqaUkEfHQLALWYi4",
                     "169QZnRqzNoQC6gcLFdTNfYPTRx4VkZn89",
                     "18h8kPb4RFJL1gMyVaKSoKz4LmBRsMsdD6",
                     "1GazoWKznZnkJs2rgUoADBfNoHcxWR6uS8",
                     "14AEZEacXmnBojoBcS9Er2Ma4sUG7Ey1pU",
                     "1LjBL9rDSNWqDZMyGr3h1H7XrSTxzLYhAu"]

    assert [crypto.HDPublicKey.from_parent(ext_chain_key, i).address() for i in range(20)] == ext_addresses
