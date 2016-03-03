# standard python imports
import os
import unittest.mock as mock

# 3rd party imports
import pytest
import mnemonic

# two1 imports
import two1
from two1.lib import wallet as _wallet
from two1.lib.blockchain import twentyone_provider
from two1.lib import server
from two1.lib import bitrequests
from two1.tests import mock as mock_objects
from two1.commands import doctor as doc
# importing classes here to fix name conflicts
from two1.commands.util.config import Config
from two1.lib.server.rest_client import TwentyOneRestClient
from two1.lib.server.machine_auth_wallet  import MachineAuthWallet


def pytest_cmdline_preparse(args):
    """ Auto adds a few usefull command line args

        From the help text:
        -r chars              show extra test summary info as specified by chars
                              (f)ailed, (E)error, (s)skipped, (x)failed, (X)passed
                              (w)pytest-warnings (a)all.

        --color=color         color terminal output (yes/no/auto).
        --durations=N         show N slowest setup/test durations (N=0 for all).
    """
    args += ['-r fExw', '--color=yes', '--durations=5']


@pytest.fixture()
def config(tmpdir):
    """ Fixture that injects a Config

    Returns:
        Config: an initialized config object
    """
    config_file = str(tmpdir.join("two1.json"))
    wallet_path = str(tmpdir.mkdir("wallet").join("wallet.json"))
    return Config(config_file=config_file, config=dict(wallet_path=wallet_path))


@pytest.fixture(scope="session")
def username(request):
    """Fixture that injects the environment variable USER_NAME

    Returns:
        str: username if given, otherwise an empty string
    """
    return os.environ['USER_NAME'] if 'USER_NAME' in os.environ else ""


@pytest.fixture(scope="session")
def password(request):
    """Fixture that injects the environment variable PASSWORD

    Returns:
        str: password if given, otherwise an empty string
    """
    return os.environ['PASSWORD'] if 'PASSWORD' in os.environ else ""


@pytest.fixture()
def wallet(config):
    """ Fixture that injects a Two1Wallet

        Uses py.test's tmpdir to create a temporary directory to store the
        wallet files. If the environment has WALLET_MNEMONIC set, this
        fixture will restore a wallet from the specified mnemonic. This is
        usefull for using the same wallet for testing to manage payouts. If
        WALLET_MNEMONIC is not set then a new wallet is created.

    Returns:
        two1.lib.wallet.Two1Wallet: initialized wallet with a wallet path in a
            temp directory.
    """
    # use standard provider
    data_provider = twentyone_provider.TwentyOneProvider(two1.TWO1_PROVIDER_HOST)

    # use mnemonic to create a wallet
    wallet_mnemonic = os.environ['WALLET_MNEMONIC'] if 'WALLET_MNEMONIC' in os.environ else None
    if wallet_mnemonic:
        m = mnemonic.Mnemonic(language='english')

        # ensure mnemonic is valid
        assert m.check(wallet_mnemonic)

        # creates a wallet from mnemonic
        wallet = _wallet.Two1Wallet.import_from_mnemonic(data_provider=data_provider, mnemonic=wallet_mnemonic)

        # writes the file to the tempdir
        wallet.to_file(config.wallet_path)

        return wallet
    else:
        # creates a new wallet
        wallet_options = dict(data_provider=data_provider, wallet_path=config.wallet_path)

        # ensures the wallet is configured correctly
        assert _wallet.Two1Wallet.configure(wallet_options)

        return _wallet.Wallet(config.wallet_path, data_provider)


@pytest.fixture()
def machine_auth_wallet(wallet):
    """ Fixture which injects a MachineAuthWallet

    Returns:
        MachineAuthWallet: machine auth wallet
    """
    return MachineAuthWallet(wallet)


@pytest.fixture()
def rest_client(machine_auth_wallet):
    """ Fixture that injects a TwentyOneRestClient

        This rest client is created without a username. If a test need to
        have a user "logged  in" then use the logged_in_rest_client fixture

    Returns:
       TwentyOneRestClient: an initialized rest client object
    """
    return TwentyOneRestClient(two1.TWO1_HOST, machine_auth_wallet)


@pytest.fixture()
def logged_in_rest_client(machine_auth_wallet, username, password):
    """ Fixture that injects a logged in TwentyOneRestClient

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


@pytest.fixture()
def doctor(config):
    """ Fixture that injects a Doctor object initialized with a mock_config

    Returns:
        Doctor: doctor object initialzied with a mock config
    """
    return doc.Doctor(config)


@pytest.fixture()
def mock_wallet():
    """ Fixture that injects a MockTwo1Wallet

    Returns:
        MockTwo1Wallet: an initialized mock two1 wallet
    """
    return mock_objects.MockTwo1Wallet()


@pytest.fixture()
def mock_config(mock_wallet):
    """ Fixture that injects a MockConfig

    Config.log is mocked to capture all log calls to test for
    appropriate output being printed to stdout.

    Returns:
        MockConfig: an mock config object initialized with a mock wallet
    """
    _mock_config = mock_objects.MockConfig()
    _mock_config.log = mock.Mock()
    _mock_config.machine_auth = MachineAuthWallet(mock_wallet)
    return _mock_config


@pytest.fixture()
def mock_rest_client(mock_config, mock_wallet):
    """ Fixture that injects a MockTwentyOneRestClient

    Returns:
        MockTwentyOneRestClient: an mock rest client initialized with a mock config and mock wallet
    """
    machine_auth = MachineAuthWallet(mock_wallet)
    _mock_rest_client = mock_objects.MockTwentyOneRestClient(None, machine_auth, mock_config.username)
    return _mock_rest_client


@pytest.yield_fixture()
def patch_click():
    """ Fixture that injects a patched click.echo function

        Patching click.echo to capture all output in a mock
        to use functions like mock.assert_called_once_with().

    Note:
        Using a yield fixture here to ensure the patch decorator
        doesn't clean up the mock like it would if this was a regular
        fixture.

    Returns:
        MagicMock: a mock object of click.echo function
    """
    with mock.patch('click.echo') as _patch_click:
        yield _patch_click


@pytest.fixture()
def patch_bitrequests(monkeypatch, mock_config, mock_wallet):
    """ Fixture that injects a MockBitRequests monketpatches the regular BitRequests

    Returns:
        MockBitRequests: a mock bitrequests object
    """
    _patch_bitrequests = mock_objects.MockBitRequests(MachineAuthWallet(mock_wallet), mock_config.username)
    monkeypatch.setattr(bitrequests.BitTransferRequests, 'request', _patch_bitrequests.request)
    monkeypatch.setattr(bitrequests.BitTransferRequests, 'get_402_info', _patch_bitrequests.get_402_info)
    return _patch_bitrequests


@pytest.fixture()
def patch_rest_client(monkeypatch, mock_config, mock_wallet):
    """ Fixture that injects a MockTwentyOneRestClient that monkeypathces the regular TwentyOneRestClient

    Returns:
        MockTwentyOneRestClient: a mock rest client object
    """
    machine_auth = MachineAuthWallet(mock_wallet)
    _patch_rest_client = mock_objects.MockTwentyOneRestClient(None, machine_auth, mock_config.username)
    for mock_function in mock_objects.MockTwentyOneRestClient.DEFAULT_VALUES.keys():
        monkeypatch.setattr(server.rest_client.TwentyOneRestClient, mock_function, getattr(_patch_rest_client, mock_function))
    return _patch_rest_client

