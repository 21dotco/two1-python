"""Unit tests for `21 config`."""
import sys
import json
import pytest
import unittest.mock as mock
from io import TextIOWrapper, BytesIO
from contextlib import contextmanager

import two1
import two1.wallet as wallet
import two1.commands.util.config as config
import two1.commands.util.exceptions as exceptions
import two1.commands.util.uxstring as uxstring


CONFIG_DATA = json.dumps(dict(
    contact='two1@21.co', maxspend=25000, sellprice=11000, stderr='.two1/two1.stderr',
    username='satoshi', mining_auth_pubkey='i_haz_key', stdout='.two1/two1.stdout',
    auto_update=False, verbose=False, sortby='price',
    collect_analytics=True,
    zt_upgraded=True,  # To prevent user prompts during testing
))
PARTIAL_CONFIG_DATA = json.dumps(dict(
    contact='21@21.co',
    zt_upgraded=True,   # To prevent user prompts during testing
))


@contextmanager
def capture_stdout(command, *args, **kwargs):
    """Captures stdout"""
    old_stdout = sys.stdout
    sys.stdout = TextIOWrapper(BytesIO(), sys.stdout.encoding)
    command(*args, **kwargs)
    # get output
    sys.stdout.seek(0)
    out = sys.stdout.read()
    # restore stdout
    sys.stdout.close()
    sys.stdout = old_stdout
    yield out


@contextmanager
def capture_stderr(command, *args, **kwargs):
    """Captures stderr"""
    old_stderr = sys.stderr
    sys.stderr = TextIOWrapper(BytesIO(), sys.stderr.encoding)
    command(*args, **kwargs)
    # get output
    sys.stderr.seek(0)
    err = sys.stderr.read()
    # restore stderr
    sys.stderr.close()
    sys.stderr = old_stderr
    yield err


@mock.patch('os.path.exists', mock.Mock(return_value=True))
@mock.patch('two1.commands.util.config.open', mock.mock_open(read_data=CONFIG_DATA), create=True)
def test_basic_config():
    """Test Config object can load a file and access its settings."""
    c = config.Config('config_file')

    assert c.username == 'satoshi'
    assert c.sellprice == 11000
    assert c.contact == 'two1@21.co'
    assert c.stdout == '.two1/two1.stdout'
    assert c.stderr == '.two1/two1.stderr'
    assert c.sortby == 'price'
    assert c.maxspend == 25000
    assert c.verbose is False
    assert c.mining_auth_pubkey == 'i_haz_key'
    assert c.auto_update is False
    assert c.wallet_path == wallet.Two1Wallet.DEFAULT_WALLET_PATH
    assert c.collect_analytics is True


@mock.patch('os.path.exists', mock.Mock(return_value=True))
@mock.patch('two1.commands.util.config.open', mock.mock_open(read_data=PARTIAL_CONFIG_DATA), create=True)
def test_default_config():
    """Test Config object loads defualt settings when file is incomplete."""
    c = config.Config('config_file')

    assert c.username is None
    assert c.sellprice == 10000
    assert c.contact == "21@21.co"
    assert c.stdout == ".two1/two1.stdout"
    assert c.stderr == ".two1/two1.stderr"
    assert c.sortby == "price"
    assert c.maxspend == 20000
    assert c.verbose is False
    assert c.mining_auth_pubkey is None
    assert c.auto_update is False
    assert c.wallet_path == wallet.Two1Wallet.DEFAULT_WALLET_PATH
    assert c.collect_analytics is True


@mock.patch('os.path.exists', mock.Mock(return_value=True))
def test_save_config():
    """Test Config object can save to update a file."""
    mock_config = mock.mock_open(read_data=CONFIG_DATA)
    with mock.patch('two1.commands.util.config.open', mock_config, create=True):
        c = config.Config('config_file')

    num_config_keys = len(c.state.keys())

    # Update an existing key and add a new one
    with mock.patch('two1.commands.util.config.open', mock_config, create=True):
        c.set('username', 'TEST_USERNAME', should_save=True)
        c.set('some_list_key', [123, 456, 789], should_save=True)

    # Import the newly saved configuration file
    new_config = json.loads(mock_config.return_value.write.call_args[0][0])

    mock_config.assert_called_with('config_file', mode='w')
    assert c.username == 'TEST_USERNAME'
    assert c.some_list_key == [123, 456, 789]
    assert new_config['username'] == 'TEST_USERNAME'
    assert new_config['some_list_key'] == [123, 456, 789]
    assert len(new_config.keys()) == num_config_keys + 1


@mock.patch('os.path.exists', mock.Mock(return_value=True))
@mock.patch('two1.TWO1_VERSION', '0.0.0')
@mock.patch('two1.commands.util.config.version.get_latest_two1_version_pypi', mock.Mock(return_value='3.0.0'))
def test_prompts_update_needed():
    """Test Config object will suggest update if needed."""
    tmp_config_data = json.loads(CONFIG_DATA)
    # set an old timestamp
    tmp_config_data['last_update_check'] = 0.0
    mock_config = mock.mock_open(read_data=json.dumps(tmp_config_data))
    with mock.patch('two1.commands.util.config.Config.save', return_value=None):
        with mock.patch('two1.commands.util.config.open', mock_config, create=True):
            with capture_stderr(
                    config.Config, 'config_file', check_update=True) as output:
                output = output.strip()
                assert(len(output) > 0)
                assert(output in uxstring.UxString.update_required)


@mock.patch('os.path.exists', mock.Mock(return_value=True))
@mock.patch('two1.TWO1_VERSION', '0.0.0')
@mock.patch('two1.commands.util.config.version.get_latest_two1_version_pypi', mock.Mock(return_value='3.0.0'))
def test_needs_update_legacy_last_update_check():
    """Test for a legacy two1.json with an older last_update_check, and that
    it does not throw an error"""
    mock_config = mock.mock_open(read_data=CONFIG_DATA)
    with mock.patch('two1.commands.util.config.open', mock_config, create=True):
        c = config.Config('config_file')
        c.set('last_update_check', "", should_save=True)
        try:
            c.check_update()
        except ValueError:
            pytest.fail("Error dealing with legacy timestamp")


@mock.patch('os.path.exists', mock.Mock(return_value=True))
@mock.patch('two1.commands.util.config.version.get_latest_two1_version_pypi', mock.Mock(return_value='3.0.0'))
def test_last_update_check_set():
    """Asert last_update_check is set in a config with none."""
    mock_config = mock.mock_open(read_data=CONFIG_DATA)
    assert 'last_update_check' not in CONFIG_DATA
    with mock.patch('two1.commands.util.config.open', mock_config, create=True):
        conf = config.Config('config_file', check_update=True)
        # last_update_check should now be set after
        # initalizing the config object.
        assert hasattr(conf, 'last_update_check')
        assert 'last_update_check' in json.loads(
            mock_config.return_value.write.call_args[0][0])


@mock.patch('os.path.exists', mock.Mock(return_value=True))
@mock.patch('two1.commands.util.config.open', mock.mock_open(read_data=CONFIG_DATA), create=True)
@mock.patch('two1.commands.util.config.version.get_latest_two1_version_pypi', mock.Mock(return_value=two1.TWO1_VERSION))
def test_needs_old_last_update_check_with_new_version():
    """Test for a last_update_check more than 3600 seconds ago, but version is new
    and that it does not suggest an update"""
    mock_config = mock.mock_open(read_data=CONFIG_DATA)
    with mock.patch('two1.commands.util.config.open', mock_config, create=True):
        c = config.Config('config_file', check_update=True)
        c.set('last_update_check', 000000.000, should_save=True)

    with capture_stdout(config.Config, 'config_file', check_update=True) as output:
        assert len(output.strip()) == 0


@mock.patch('os.path.exists', mock.Mock(return_value=True))
def test_no_config_file_exists():
    """Test that a new `two1.json` file is created if it doesn't exist."""
    mock_config = mock.mock_open()
    mock_config.side_effect = [FileNotFoundError(), mock.DEFAULT]
    with mock.patch('two1.commands.util.config.Config.save', return_value=None):
        with mock.patch('two1.commands.util.config.open', mock_config, create=True):
            config.Config('config_file', config=json.loads(PARTIAL_CONFIG_DATA))

    assert mock_config.call_count == 2
    dc = json.loads(mock_config.return_value.write.call_args[0][0])
    mock_config.assert_called_with('config_file', mode='w')

    assert dc['username'] is None
    assert dc['sellprice'] == 10000
    assert dc['contact'] == "two1@21.co"
    assert dc['stdout'] == ".two1/two1.stdout"
    assert dc['stderr'] == ".two1/two1.stderr"
    assert dc['sortby'] == "price"
    assert dc['maxspend'] == 20000
    assert dc['verbose'] is False
    assert dc['mining_auth_pubkey'] is None
    assert dc['auto_update'] is False
    assert dc['wallet_path'] == wallet.Two1Wallet.DEFAULT_WALLET_PATH
    assert dc['collect_analytics'] is True


@mock.patch('os.path.exists', mock.Mock(return_value=True))
def test_invalid_config_file():
    """Test that an invalid `two1.json` file cannot be imported."""
    mock_config = mock.mock_open(mock=mock.Mock(side_effect=ValueError))
    with mock.patch('two1.commands.util.config.open', mock_config, create=True), pytest.raises(exceptions.FileDecodeError):  # nopep8
        config.Config('config_file')

    mock_config.assert_called_with('config_file', mode='r')


@mock.patch('os.path.exists', mock.Mock(return_value=True))
@mock.patch('two1.commands.util.config.open', mock.mock_open(read_data=CONFIG_DATA), create=True)
def test_config_repr():
    """Test Config object can be displayed nicely in `print` statements."""
    c = config.Config('config_file')
    printed = c.__repr__()

    assert 'satoshi' in printed
    assert '11000' in printed
    assert 'two1@21.co' in printed
    assert '.two1/two1.stdout' in printed
    assert '.two1/two1.stderr' in printed
    assert 'price' in printed
    assert '25000' in printed
    assert 'False' in printed
    assert 'i_haz_key' in printed
    assert 'False' in printed
    assert wallet.Two1Wallet.DEFAULT_WALLET_PATH in printed
    assert 'True' in printed
