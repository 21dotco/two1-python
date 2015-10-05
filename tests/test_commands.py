import os
import unittest
import mock

from mock import patch

from two1 import config
import two1.cli as cli
from click.testing import CliRunner
from click import ClickException


TEST_FOLDER = os.path.join(os.path.dirname(__file__), 'test_data')
TEST_FILE = os.path.join(TEST_FOLDER, 'red.jpeg')
TEST_CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'test_config.json')


def get_args(command, *args):
    a = ['--config-file', TEST_CONFIG_FILE, '--config', 'testwallet', 'y', command]
    a += args
    return a


class TestSell(unittest.TestCase):
    @patch('two1.lib.update.get_latest_version')
    def test_builtins(self, f):
        f.return_value = config.TWO1_VERSION
        runner = CliRunner()
        # two1 sell --builtin
        result = runner.invoke(cli.main, get_args('sell', '--builtin'))
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn('barcode/generate-qr', result.output, result.output)

    @patch('two1.lib.update.get_latest_version')
    def test_sell_builtins(self, f):
        f.return_value = config.TWO1_VERSION
        runner = CliRunner()
        # two1 sell language/translate two1.djangobitcoin.misc
        result = runner.invoke(cli.main, get_args('sell', 'language/translate', 'two1.djangobitcoin.misc'))
        self.assertEqual(result.exit_code, 0, result.output)

    @patch('two1.lib.update.get_latest_version')
    def test_sell_static_folder(self, f):
        f.return_value = config.TWO1_VERSION
        runner = CliRunner()
        # two1 sell serve/kittens two1.djangobitcoin.static_serve --path ~/Documents/Kittens --price 10000
        result = runner.invoke(cli.main,
                               get_args('sell', 'serve/kittens', 'two1.djangobitcoin.static_serve',
                                        '--path', TEST_FOLDER, '--price', '10000'))
        self.assertEqual(result.exit_code, 0, result.output)

    @patch('two1.lib.update.get_latest_version')
    def test_sell_static_file(self, f):
        f.return_value = config.TWO1_VERSION
        runner = CliRunner()
        # two1 sell serve/kittens/kitty.jpg two1.djangobitcoin.static_serve --path ~/Documents/Kittens/red.jpeg --price 10000
        result = runner.invoke(cli.main,
                               get_args('sell', 'serve/kittens/kitty/kitty.jpg', 'two1.djangobitcoin.static_serve',
                                        '--path', TEST_FILE, '--price', '10000'))
        self.assertEqual(result.exit_code, 0, result.output)

    @patch('two1.lib.update.get_latest_version')
    def test_sell_static_folder_with_file_fail(self, f):
        f.return_value = config.TWO1_VERSION
        runner = CliRunner()
        # two1 sell serve/kittens two1.djangobitcoin.static_serve --path ~/Documents/Kittens/red.jpg --price 10000
        result = runner.invoke(cli.main,
                               get_args('sell', 'serve/kittens', 'two1.djangobitcoin.static_serve',
                                        '--path', TEST_FILE, '--price', '10000'))
        self.assertNotEqual(result.exit_code, 0, result.output)

    @patch('two1.lib.update.get_latest_version')
    def test_sell_static_file_with_folder_fail(self, f):
        f.return_value = config.TWO1_VERSION
        runner = CliRunner()
        # two1 sell serve/kittens/kitty.jpg two1.djangobitcoin.static_serve --path ~/Documents/Kittens --price 10000
        result = runner.invoke(cli.main,
                               get_args('sell', 'serve/kittens/kitty.jpg', 'two1.djangobitcoin.static_serve',
                                        '--path', TEST_FOLDER, '--price', '10000'))
        self.assertNotEqual(result.exit_code, 0, result.output)

    @patch('two1.lib.update.get_latest_version')
    def test_sell_static_folder_no_folder_fail(self, f):
        f.return_value = config.TWO1_VERSION
        runner = CliRunner()
        # two1 sell serve/kittens two1.djangobitcoin.static_serve --path ~/Documents/Kittens --price 10000
        result = runner.invoke(cli.main,
                               get_args('sell', 'serve/kittens', 'two1.djangobitcoin.static_serve',
                                        '--path', TEST_FOLDER + 'X', '--price', '10000'))
        self.assertNotEqual(result.exit_code, 0, result.output)

    @patch('two1.lib.update.get_latest_version')
    def test_sell_static_file_no_file_fail(self, f):
        f.return_value = config.TWO1_VERSION
        runner = CliRunner()
        # two1 sell serve/kittens/kitty.jpg two1.djangobitcoin.static_serve --path ~/Documents/Kittens/red.jpeg --price 10000
        result = runner.invoke(cli.main,
                               get_args('sell', 'serve/kittens/kitty/kitty.jpg', 'two1.djangobitcoin.static_serve',
                                        '--path', TEST_FILE + 'X', '--price', '10000'))
        self.assertNotEqual(result.exit_code, 0, result.output)


class TestRate(unittest.TestCase):
    def setUp(self):
        """ Automatically called before every test method is run """
        self.runner = CliRunner()
        # exit_code 0 means everything went well
        # exit_code 1 means a ClickException; an exception Click can handle and show to the user
        # exit_code 2 means a UsageError; an internal exception that signals a usage error
        #rating = Rating()
        #rating.purchase = None
        #rating.rating = None
        #rating.review = None

        #self.stuff =
        #fixtures = ['db_test_data']
        #print(fixtures)

    def tearDown(self):
        """ Automatically called after every test method is run """
        self.runner = None

    def test_builtin_help_method(self):
        """ $two1 rate --help """
        self.result = self.runner.invoke(cli.main, get_args('rate', '--help'))
        self.assertEqual(self.result.exit_code, 0)

    def test_rate_existing_purchase(self):
        """ $two1 rate [purchase] on an existing purchase """
        #self.runner.invoke(cli.main, get_args('rate'))
        self.result = self.runner.invoke(cli.main,
            ['rate', 'c833e922-4cc1-4f6a-9d1f-181c839c0a08', '4.0'])
        self.assertEqual(self.result.exit_code, 0)

    def test_rate_nonexisting_endpoint(self):
        """ $two1 rate [purchase] on a nonexisting purchase """
        self.runner.invoke(cli.main, get_args('rate'))
        self.result = self.runner.invoke(cli.main,
            ['rate', 'purchase-uuid-not-here', '1.0'])
        self.assertEqual(self.result.exit_code, 1)

    def test_rate_missing_purchase_parameter(self):
        """ $two1 rate with a missing purchase parameter """
        pass

    def test_rate_missing_rating_parameter(self):
        """ $two1 rate with a missing rating parameter """
        pass

    def test_rate_unknown_parameter(self):
        """ $two1 rate with an unknown parameter """
        pass

    def test_rate_raise_http_500_error(self):
        """ $two1 rate and server returns HTTP 500 response """
        pass

    def test_rate_rating_has_numbers_below_scale(self):
        """ $two1 rate [purchase] with [rating] below 0.0 """
        pass

    def test_rate_rating_has_numbers_above_scale(self):
        """ $two1 rate [purchase] with [rating] above 0.0 """
        pass

    def test_rate_rating_has_numbers_in_scale(self):
        """ $two1 rate [purchase] with [rating] between 0.0 and 5.0 """
        pass

    def test_rate_repeated_ratings_on_same_endpoint(self):
        """ $two1 rate [purchase] [rating] and there is an existing rating """
        pass

    def test_rate_rating_with_large_float_should_round_up(self):
        """ $two1 rate [purchase] [rating] should round up """
        pass


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
        assert isinstance(result.exception, SystemExit)
        self.assertEqual(result.exit_code, 1)

    def test_publish_missing_all_args(self):
        # test for missing arg error messages
        runner = CliRunner()
        result = runner.invoke(cli.main, get_args('publish'))
        assert 'Missing required arg PATH' in result.output
        assert 'Missing required arg NAME' in result.output
        assert 'Missing required arg DESCRIPTION' in result.output
        assert 'Missing required arg PRICE' in result.output
        assert 'Missing required arg DEVICE_UUID' in result.output
        assert isinstance(result.exception, SystemExit)
        self.assertEqual(result.exit_code, 1)

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

if __name__ == '__main__':
    unittest.main()
