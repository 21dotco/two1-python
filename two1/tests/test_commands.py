import unittest

import os
# from mock import patch
import pytest
from two1.commands import config
import two1.cli as cli
from click.testing import CliRunner
from two1.tests import test_utils

TEST_FOLDER = os.path.join(os.path.dirname(__file__), 'test_data')
TEST_FILE = os.path.join(TEST_FOLDER, 'red.jpeg')
TEST_CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'test_config.json')


@pytest.fixture(scope="session", autouse=True)
def prepare_wallet():
    test_utils.setup_wallet()


def get_args(command, *args):
    a = ['--config-file', TEST_CONFIG_FILE, '--config', 'testwallet', 'y', command]
    a += args
    return a


# DISABLED UNTIL WE REWRITE STATIC SERVER
class TestSell(unittest.TestCase):
    pass
    # @patch('two1.commands.update.get_latest_version')
    # def test_builtins(self, f):
    #     f.return_value = config.TWO1_VERSION
    #     runner = CliRunner()
    #     # two1 sell --builtin
    #     result = runner.invoke(cli.main, get_args('sell', '--builtin'))
    #     self.assertEqual(result.exit_code, 0, result.output)
    #     self.assertIn('barcode/generate-qr', result.output, result.output)

    # @patch('two1.commands.update.get_latest_version')
    # def test_sell_builtins(self, f):
    #     f.return_value = config.TWO1_VERSION
    #     runner = CliRunner()
    #     # two1 sell language/translate two1.examples.misc
    #     result = runner.invoke(cli.main, get_args('sell', 'language/translate', 'two1.examples.server.misc'))
    #     self.assertEqual(result.exit_code, 0, result.output)

    # @patch('two1.commands.update.get_latest_version')
    # def test_sell_static_folder(self, f):
    #     f.return_value = config.TWO1_VERSION
    #     runner = CliRunner()
    #     # two1 sell serve/kittens two1.examples.static_serve --path ~/Documents/Kittens --price 10000
    #     result = runner.invoke(cli.main,
    #                            get_args('sell', 'serve/kittens', 'two1.examples.static_serve',
    #                                     '--path', TEST_FOLDER, '--price', '10000'))
    #     self.assertEqual(result.exit_code, 0, result.output)

    # @patch('two1.commands.update.get_latest_version')
    # def test_sell_static_file(self, f):
    #     f.return_value = config.TWO1_VERSION
    #     runner = CliRunner()
    #     # two1 sell serve/kittens/kitty.jpg two1.examples.static_serve --path ~/Documents/Kittens/red.jpeg --price 10000
    #     result = runner.invoke(cli.main,
    #                            get_args('sell', 'serve/kittens/kitty/kitty.jpg', 'two1.examples.static_serve',
    #                                     '--path', TEST_FILE, '--price', '10000'))
    #     self.assertEqual(result.exit_code, 0, result.output)
    #
    # @patch('two1.commands.update.get_latest_version')
    # def test_sell_static_folder_with_file_fail(self, f):
    #     f.return_value = config.TWO1_VERSION
    #     runner = CliRunner()
    #     # two1 sell serve/kittens two1.examples.static_serve --path ~/Documents/Kittens/red.jpg --price 10000
    #     result = runner.invoke(cli.main,
    #                            get_args('sell', 'serve/kittens', 'two1.examples.static_serve',
    #                                     '--path', TEST_FILE, '--price', '10000'))
    #     self.assertNotEqual(result.exit_code, 0, result.output)
    #
    # @patch('two1.commands.update.get_latest_version')
    # def test_sell_static_file_with_folder_fail(self, f):
    #     f.return_value = config.TWO1_VERSION
    #     runner = CliRunner()
    #     # two1 sell serve/kittens/kitty.jpg two1.examples.static_serve --path ~/Documents/Kittens --price 10000
    #     result = runner.invoke(cli.main,
    #                            get_args('sell', 'serve/kittens/kitty.jpg', 'two1.examples.static_serve',
    #                                     '--path', TEST_FOLDER, '--price', '10000'))
    #     self.assertNotEqual(result.exit_code, 0, result.output)
    #
    # @patch('two1.commands.update.get_latest_version')
    # def test_sell_static_folder_no_folder_fail(self, f):
    #     f.return_value = config.TWO1_VERSION
    #     runner = CliRunner()
    #     # two1 sell serve/kittens two1.examples.static_serve --path ~/Documents/Kittens --price 10000
    #     result = runner.invoke(cli.main,
    #                            get_args('sell', 'serve/kittens', 'two1.examples.static_serve',
    #                                     '--path', TEST_FOLDER + 'X', '--price', '10000'))
    #     self.assertNotEqual(result.exit_code, 0, result.output)
    #
    # @patch('two1.commands.update.get_latest_version')
    # def test_sell_static_file_no_file_fail(self, f):
    #     f.return_value = config.TWO1_VERSION
    #     runner = CliRunner()
    #     # two1 sell serve/kittens/kitty.jpg two1.examples.static_serve --path ~/Documents/Kittens/red.jpeg --price 10000
    #     result = runner.invoke(cli.main,
    #                            get_args('sell', 'serve/kittens/kitty/kitty.jpg', 'two1.examples.static_serve',
    #                                     '--path', TEST_FILE + 'X', '--price', '10000'))
    #     self.assertNotEqual(result.exit_code, 0, result.output)


class TestRate(unittest.TestCase):
    def test_builtins(self):
        """ $two1 rate --help """
        runner = CliRunner()
        result = runner.invoke(cli.main, get_args('rate', '--help'))
        self.assertEqual(result.exit_code, 0)


class TestPublish(unittest.TestCase):
    def test_publish_valid_endpoint(self):
        # publish endpoint
        # import random
        # runner = CliRunner()
        # random_name = random.getrandbits(255)
        # result = runner.invoke(cli.main, get_args('publish', str(random_name), 'name', 'desc', '1000', '679e3ab3-c3b5-4aea-a8ad-eeef037fc248'))
        # assert not result.exception
        # self.assertEqual(result.exit_code, 0)
        pass

    def test_publish_non_integer_price(self):
        # test for price must be integer error message
        runner = CliRunner()
        result = runner.invoke(cli.main, get_args('publish', 'path', 'name', 'desc', '1000dddd', '679e3ab3-c3b5-4aea-a8ad-eeef037fc248'))
        assert 'arg PRICE must be a valid integer' in result.output
        self.assertEqual(result.exit_code, 0)

    def test_publish_missing_all_args(self):
        # test for missing arg error messages
        runner = CliRunner()
        result = runner.invoke(cli.main, get_args('publish'))
        assert 'Missing required arg PATH' in result.output
        assert 'Missing required arg NAME' in result.output
        assert 'Missing required arg DESCRIPTION' in result.output
        assert 'Missing required arg PRICE' in result.output
        assert 'Missing required arg DEVICE_UUID' in result.output
        self.assertEqual(result.exit_code, 0)

    def test_publish_nonexistant_endpoint(self):
        # todo: if endpoint doesn't exist on device, don't attempt publish
        # assert not result.exception
        pass

    def test_publish_all(self):
        # todo: test publishing all ulisted endpoints
        # assert not result.exception
        pass

    def test_publish_help(self):
        runner = CliRunner()
        result = runner.invoke(cli.main, get_args('publish', '--help'))
        self.assertEqual(result.exit_code, 0)
        assert not result.exception
