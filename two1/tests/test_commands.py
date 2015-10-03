import unittest

import os
from mock import patch
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
