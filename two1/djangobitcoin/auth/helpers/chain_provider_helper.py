"""Utils to work with chain api."""
import os

from two1.blockchain.chain_provider import ChainProvider
from two1.bitcoin.txn import Transaction
from two1.bitcoin.utils import hex_str_to_bytes
from two1.bitcoin.utils import key_hash_to_address

class ChainProviderHelper(object):

    """Api interface built on top of a bitcoin provider.

    Purpose is to call lower level bitcoin api calls
    to serve higher level djangobitcoin functionality.
    """

    def __init__(self):
        """Initalization of the Chain Provider."""
        self.provider = ChainProvider(
            os.environ.get(
                "CHAIN_API_KEY_ID",
                "a96f8c3c18abe407757713a09614ba0b"
            ),
            os.environ.get(
                "CHAIN_API_KEY_SECRET",
                "a13421f9347421e88c17d8388638e311"
            )
        )

    def validate_payment(self, tx, address, amount):
        """Ensure tx, reciepient & amount are valid.

        Deconstructs a tranasction, and ensures that 
        1) Tranasaction is valid.
        2) Address the tx is paying is the address inputted
        3) The amount that the tranasction is paying
        
        Args:
            tx (str): raw signed tranasction
            address (str): base58 bitcoin address
            amount (int): bitcoin in satoshis
                
        Raises:
            ValueError: if one of the condtions are 
            invalid or not met
        """
        tx, _ = Transaction.from_bytes(
            hex_str_to_bytes(tx)
        )
        if tx.outputs[0].value != amount:
            raise ValueError("Insufficient Payment")
        payout_hash160 = tx.outputs[0].script.get_hash160()
        payout_address = key_hash_to_address(payout_hash160)
        if payout_address != address:
            raise ValueError("Incorrect Payout Address")


if __name__ == "__main__":
    cph = ChainProviderHelper()
    cph.check_payment(
        "0100000001e5dc38d25c5c7b9851781ab1f9f74f8e771fbde2dcf238f6c58e27e785c8c61e000000006b483045022100f7e10fe23f9953b21f69702ec3ed519289d8610865264c59b775805b939ca19e022077cee131af63bf40b65f9a76d091ac038d8a831708a46ac5cf5498c315f64ca70121036bcf5352a118062da9bab4a61603d31ba1ab1c586816f31b1dbe4dcaf8af9f6affffffff0288130000000000001976a91470d2d38722066e8458b5848c6623a7b92190ba2988ac2c330000000000001976a914fa5fa606f99d3bcc61368dd2bcf3f7844876a76988ac00000000",
        "1BHZExCqojqzmFnyyPEcUMWLiWALJ32Zp5",
        5000
    )
