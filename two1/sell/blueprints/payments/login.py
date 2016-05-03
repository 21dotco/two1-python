import os
import base64

import two1
from two1.commands.util.config import Config
from two1.server import machine_auth_wallet
from two1.wallet.two1_wallet import Two1Wallet
from two1.wallet.daemonizer import get_daemonizer
from two1.server import rest_client as _rest_client
from two1.blockchain.twentyone_provider import TwentyOneProvider


def login_21():
    """ Restore wallet to disk and log in to 21.
    """

    d = None
    try:
        d = get_daemonizer()
    except OSError as e:
        pass

    if d:
        d.stop()

    mnemonic = os.environ["TWO1_WALLET_MNEMONIC"]

    provider = TwentyOneProvider()
    wallet = Two1Wallet.import_from_mnemonic(provider, mnemonic)

    if not os.path.exists(os.path.dirname(Two1Wallet.DEFAULT_WALLET_PATH)):
        os.makedirs(os.path.dirname(Two1Wallet.DEFAULT_WALLET_PATH))
    wallet.to_file(Two1Wallet.DEFAULT_WALLET_PATH)

    # login
    config = Config()
    machine_auth = machine_auth_wallet.MachineAuthWallet(wallet)

    username = os.environ["TWO1_USERNAME"]
    password = os.environ["TWO1_PASSWORD"]

    rest_client = _rest_client.TwentyOneRestClient(two1.TWO1_HOST, machine_auth, username)

    machine_auth_pubkey_b64 = base64.b64encode(machine_auth.public_key.compressed_bytes).decode()
    payout_address = machine_auth.wallet.current_address

    rest_client.login(payout_address=payout_address, password=password)

    config.set("username", username)
    config.set("mining_auth_pubkey", machine_auth_pubkey_b64)
    config.save()


if __name__ == '__main__':
    login_21()
