"""Unit tests for `21 config`."""
import json
import pytest
import unittest.mock as mock

import two1.wallet as wallet
import two1.commands.util.config as config
import two1.commands.util.exceptions as exceptions

CONFIG_DATA = json.dumps(dict(
    contact='two1@21.co', maxspend=25000, sellprice=11000, stderr='.two1/two1.stderr',
    username='satoshi', mining_auth_pubkey='i_haz_key', stdout='.two1/two1.stdout',
    auto_update=False, verbose=False, sortby='price',
    collect_analytics=True))
PARTIAL_CONFIG_DATA = json.dumps(dict(contact='21@21.co'))


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
    assert c.collect_analytics is False


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
def test_no_config_file_exists():
    """Test that a new `two1.json` file is created if it doesn't exist."""
    mock_config = mock.mock_open()
    mock_config.side_effect = [FileNotFoundError(), mock.DEFAULT]
    with mock.patch('two1.commands.util.config.Config.save', return_value=None):
        with mock.patch('two1.commands.util.config.open', mock_config, create=True):
            c = config.Config('config_file')

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
    assert dc['collect_analytics'] is False


@mock.patch('os.path.exists', mock.Mock(return_value=True))
def test_invalid_config_file():
    """Test that an invalid `two1.json` file cannot be imported."""
    mock_config = mock.mock_open(mock=mock.Mock(side_effect=ValueError))
    with mock.patch('two1.commands.util.config.open', mock_config, create=True), pytest.raises(exceptions.FileDecodeError):
        c = config.Config('config_file')

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
