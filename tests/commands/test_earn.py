"""Test the 21 earn command."""
import pytest

from two1.cli import parse_config
import two1.channels as channels
from two1.commands.status import _get_balances
from two1.commands.faucet import _faucet as faucet


class Stub:
    pass


@pytest.fixture(scope="module")
def userdata():
    """Get userdata and set up a mock server.

    In this example, the MockEarnRestClient yields what the server
    expects to send the client for each attempt at earning bitcoin.
    """
    ud = Stub()
    obj = parse_config()
    ud.client = obj['client']
    ud.config = obj['config']
    ud.wallet = obj['wallet']
    ud.username = obj['username']
    return ud


@pytest.fixture(scope="module")
def username(userdata):
    """Get username for 21 user on this machine."""
    return userdata.username


@pytest.fixture(scope="module")
def client(userdata):
    """Get MockEarnRestClient for testing the earn command."""
    return userdata.client


@pytest.fixture(scope="module")
def wallet(userdata):
    """Get wallet for the 21 user on this machine."""
    return userdata.wallet


def twentyone_balance(client, wallet):
    channel_client = channels.PaymentChannelClient(wallet)
    user_balances = _get_balances(client, wallet, channel_client)
    return user_balances.twentyone


@pytest.mark.skipif(reason="Jenkins runs test logged in as `lplp` user, but then fails")
def test_faucet_works(username, client, wallet):
    """Confirm that faucet increases off-chain buffer.

    Get the initial balance, run the faucet earning task exactly once,
    determine the amount the faucet is supposed to return, and confirm
    that the balance increased by exactly that amount.
    """
    old_satoshis = twentyone_balance(client, wallet)
    faucet(username, client, wallet)
    EXPECTED_FAUCET_EARNINGS = 20000
    new_satoshis = twentyone_balance(client, wallet)
    assert new_satoshis == old_satoshis + EXPECTED_FAUCET_EARNINGS
