# standard python imports
import os

# 3rd party imports
import pytest
import mnemonic

# two1 imports
import two1
from two1.lib import wallet as _wallet
from two1.lib.blockchain import twentyone_provider
# importing classes here to fix name conflicts
from two1.lib.server.rest_client import TwentyOneRestClient
from two1.lib.server.machine_auth_wallet  import MachineAuthWallet


@pytest.fixture(scope="session")
def username(request):
    """Fixture that provides the command line arg username

    Returns:
        str: username if given, otherwise an empty string
    """
    return os.environ['USER_NAME'] if 'USER_NAME' in os.environ else ""


@pytest.fixture(scope="session")
def password(request):
    """Fixture that provides the command line arg password

    Returns:
        str: password if given, otherwise an empty string
    """
    return os.environ['PASSWORD'] if 'PASSWORD' in os.environ else ""


@pytest.fixture()
def wallet(tmpdir):
    """ Fixture that provides an instatiated wallet

        Uses py.test's tmpdir to create a temporary directory to store the
        wallet files. If the environment has WALLET_MNEMONIC set, this
        fixture will restore a wallet from the specified mnemonic. This is
        usefull for using the same wallet for testing to manage payouts. If
        WALLET_MNEMONIC is not set then a new wallet is created.

    Returns:
        two1.lib.wallet.Two1Wallet: initialized wallet with a wallet path in a
            temp directory.
    """
    # sets the wallet path to a temp directory
    wallet_path = str(tmpdir.join('two1.json'))

    # use standart provider
    data_provider = twentyone_provider.TwentyOneProvider(two1.TWO1_PROVIDER_HOST)

    wallet_mnemonic = None
    if 'WALLET_MNEMONIC' in os.environ:
        wallet_mnemonic = os.environ['WALLET_MNEMONIC']

    # use mnemonic to create a wallet
    if wallet_mnemonic:
        m = mnemonic.Mnemonic(language='english')

        # ensure mnemonic is valid
        assert m.check(wallet_mnemonic)

        # creates a wallet from mnemonic
        wallet = _wallet.Two1Wallet.import_from_mnemonic(data_provider=data_provider, mnemonic=wallet_mnemonic)

        # writes the file to the tempdir
        wallet.to_file(wallet_path)

        return wallet
    else:
        # creates a new wallet
        wallet_options = dict(data_provider=data_provider, wallet_path=wallet_path)

        # ensures the wallet is configured correctly
        assert _wallet.Two1Wallet.configure(wallet_options)

        return _wallet.Wallet(wallet_path, data_provider)


@pytest.fixture()
def machine_auth_wallet(wallet):
    """ Fixture which provides an initialized MachineAuthWallet object

    Returns:
        MachineAuthWallet: machine auth wallet
    """
    return MachineAuthWallet(wallet)


@pytest.fixture()
def rest_client(machine_auth_wallet):
    """ Fixture that provides an initialized rest client

        This rest client is created without a username. If a test need to
        have a user "logged  in" then use the logged_in_rest_client fixture

    Returns:
       TwentyOneRestClient: an initialized rest client object
    """
    return TwentyOneRestClient(two1.TWO1_HOST, machine_auth_wallet)


@pytest.fixture()
def logged_in_rest_client(machine_auth_wallet, username, password):
    """ Fixture that provides an initialized and logged in rest client

        This rest client is created with the given username in the USERNAME
        environment variable. This fixture also logs in by posting to the login
        api.

    Returns:
       TwentyOneRestClient: an initialized rest client object
    """
    # ensure the user has given an account username and password
    assert password, "Error: PASSWORD was not given as an environment variable"
    assert username, "Error: USER_NAME was not given as an environment variable"

    # rest client with the given username
    _rest_client = TwentyOneRestClient(two1.TWO1_HOST, machine_auth_wallet, username)

    # logs into account
    _rest_client.login(machine_auth_wallet.wallet.current_address, password)

    return _rest_client

