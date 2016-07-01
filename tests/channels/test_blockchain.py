import pytest

import two1.channels.blockchain as blockchain


@pytest.fixture(params=[
    blockchain.TwentyOneBlockchain("https://blockchain.21.co/blockchain/bitcoin"),
])
def bc(request):
    return request.param


def test_blockchain(bc):
    # Check check_confirmed()
    assert bc.check_confirmed(
        "bed5c9871fbcb6f63cd629579f532ed5dc728136e027ffdf81ccfacb7b181967", num_confirmations=492) is True
    assert bc.check_confirmed("101a4d5d9dcd7c73848f499c4c4dd5d114d9a0cb0622c34f29e5e0fa406f3f83") is False

    # Check lookup_spend_txid()
    assert bc.lookup_spend_txid("5d72866a181e37c6fe1b2624f48955f75d6c08974004d43a3bbd1e62eddfef91", 0) == "ea756854b1254b87fe6aaed036ce67d5f0749ac86e2c7fd6a917d60fb4734369"  # nopep8
    # This fails when using TwentyOneProvider with newer Insight backend.
    # Commenting out for now.
    # assert bc.lookup_spend_txid("5d72866a181e37c6fe1b2624f48955f75d6c08974004d43a3bbd1e62eddfef91", 1) == "bed5c9871fbcb6f63cd629579f532ed5dc728136e027ffdf81ccfacb7b181967"  # nopep8
    with pytest.raises(IndexError):
        bc.lookup_spend_txid("5d72866a181e37c6fe1b2624f48955f75d6c08974004d43a3bbd1e62eddfef91", 2)

    # Check lookup_tx()
    assert bc.lookup_tx("bed5c9871fbcb6f63cd629579f532ed5dc728136e027ffdf81ccfacb7b181967") == "010000000191efdfed621ebd3b3ad4044097086c5df75589f424261bfec6371e186a86725d01000000e4473044022049d1f41a867aa84266a1f5d2f6283d2b1e6ee07d068a098615d7a7868a96ed78022060c798cbb4740277cb095c399fb10ebd2716894c203527b0e6e3ed797400d10701483045022100de7c4c35c263cc2e1df1f2b06925225a72b9cb28e3b8bae4db7b078a1e4ac25c022031103dbe8993e94daa119d4c78e0bf52d3513e152d8b5bc192f8cb26ac3c683901514c50632102f1fff97def324ddea032fed4c8249113b8dce12aaf614d11bb833e587072c8a9ad6704a9a07056b1756821026179020dba5ad8275cf6389a85a00c08f3597bb8617af8148f249a4cd719ab39acffffffff02a0860100000000001976a914ffffb9d45c6cb46133f55a83c2fde9edb1c5f50688ace8030000000000001976a914314d768ce14fc1f5dffdac1e4a0ed13705d4a4a688ac00000000"  # nopep8
    assert bc.lookup_tx("101a4d5d9dcd7c73848f499c4c4dd5d114d9a0cb0622c34f29e5e0fa406f3f83") is None

    # Check broadcast_tx()
    # Broadcast existing transaction
    assert bc.broadcast_tx("0100000001d1e245f26f2354672d653122893d8e7a84f77515bbc6c29c457711f3b67fe90e010000006a47304402204fee33aed5c30e2546b0c3e211a99aeadae75c5cb8d2257eceabef6b190a6ed002205023d17c28c81db58c44213cf6687a4790528c4d123f8c13d6395f0c5ab9c1b20121039176bfb795e10d793dbfd68a11e5577296ad591154e15d9a39b26f5dca84ed69ffffffff02b0ad01000000000017a914d7b04112a5e0314ae378c8038205edf1fa98a76087952d8400000000001976a91473170178389cf8ce3570a7a4624a96ac924b999588ac00000000") == "25e0f083c7508d8f52a12f80669a54007dc989a752974c6660f09dac7017d810"  # nopep8
