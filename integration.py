import re
import pytest
from two1.cli import main
from click.testing import CliRunner
from two1.lib.util.uxstring import UxString
from two1.tests import test_utils


@pytest.fixture(scope="session", autouse=True)
def prepare_wallet():
    test_utils.setup_wallet()


def test_end_to_end():
    runner = CliRunner()
    with runner.isolated_filesystem():
        print_test_msg('help')
        run_help_msg(runner)

        print_test_msg('status')
        unconfirmed_amount, payout_address = run_two1_status(runner)

        print_test_msg('mine')
        run_two1_mine(runner, unconfirmed_amount)

        print_test_msg('search')
        endpoint = run_two1_search(runner, "weather")

        print_test_msg('buy from ' + endpoint)
        txn_id = run_two1_buy(runner, endpoint)

        print_success()
        print_test_info(payout_address, txn_id)


def run_help_msg(runner):
    result = runner.invoke(main, [])
    assert_no_error(result)
    verify_blank_two1(result.output)


def run_two1_status(runner):
    # run it without username and craete a username
    config_file = "--config-file={}".format(test_utils.rand_str(3))
    username = test_utils.rand_str(4) + "\n"
    result = runner.invoke(main, [config_file, 'status'], input=username)
    assert_no_error(result)
    verify_two1_status_no_user(result.output, username)
    payout_addrs = scrape_payout_from_status_output(result.output)

    # Creating user name
    result = runner.invoke(main, [config_file, 'status'], input=username)
    assert_no_error(result)
    verify_two1_status(result.output, username, payout_addrs)
    unconfirmed_amount = scrape_unconfirmed_amount(result.output)
    return unconfirmed_amount, payout_addrs


def run_two1_mine(runner, unconfirmed_amount):
    result = runner.invoke(main, ['mine'])
    assert_no_error(result)
    verify_two1_mine(result.output, unconfirmed_amount)


def run_two1_search(runner, query):
    result = runner.invoke(main, ['search', '--query', query])
    endpoint = verify_two1_search(result.output)
    print(result.output)
    return endpoint


def run_two1_buy(runner, endpoint):
    # todo replace the url for buy with something more elegant
    result = runner.invoke(main, ['buy',
                                  endpoint])
    assert_no_error(result)
    txn_id = verify_two1_buy(result.output)
    return txn_id


def assert_no_error(result):
    assert result.exit_code == 0, result.exception
    assert result.exception is None
    print("\n\n\n")
    print(result.output)
    print("\n\n\n")


def verify_blank_two1(output):
    assert 'Usage: main [OPTIONS] COMMAND [ARGS]...' in output
    result = all([x in output for x in
                  ['buy', 'min', 'publish', 'rate', 'search', 'sell', 'status']])
    assert result


def verify_two1_status_no_user(output, given_username):
    assert UxString.enter_username in output

    # FIXME find a better way to assert this
    username_row = 'Username              : {}'.format(given_username)
    payout_addrs_row = 'Payout Address        :'
    assert username_row in output
    assert payout_addrs_row in output


def verify_two1_status(output, username, payout_address):
    assert username in output
    assert payout_address in output


def verify_two1_mine(output, original_unconfirmed_amount):
    pool_payout = 200000
    assert "Mining" in output
    assert "Mining Complete" in output
    assert "You mined {} ฿".format(20000)

    new_unconfirmed_amount = scrape_unconfirmed_amount(output)
    assert new_unconfirmed_amount == original_unconfirmed_amount + pool_payout, \
        "original_amount={} new_amount={}".format(original_unconfirmed_amount,
                                                  new_unconfirmed_amount)


def verify_two1_search(output):
    lines = output.split("\n")
    result_lines = lines[3:-2]
    assert len(result_lines) == 3
    current_temp_api = [x for x in result_lines if "current-temperature" in x]
    assert len(current_temp_api) > 0

    api_info = current_temp_api[0].replace(" ", "").split("|")
    api_endpoint = api_info[1] + "?place=tehran"
    return api_endpoint


def verify_two1_buy(output):
    # todo add the correct verification once we have finalized the
    # output
    txn_id = scrape_txn_id_from_buy_output(output)
    return txn_id


def scrape_payout_from_status_output(output):
    # fixme find a better way to read this out of UxString
    clue = "Setting mining payout address: "
    payout_addrs_start = output[output.index(clue) + len(clue):]
    payout_end_del = payout_addrs_start.index('.\n')
    payout_addrs = payout_addrs_start[:payout_end_del]
    return payout_addrs


def scrape_unconfirmed_amount(output):
    clue = "Pending Transactions  :   "
    amount_start = output[output.index(clue) + len(clue):]
    amount_end_del = amount_start.index(' Satoshi')
    amount = amount_start[:amount_end_del]
    return int(amount)


def scrape_txn_id_from_buy_output(output):
    clue = 'txid: '
    txn_id_start = output[output.index(clue) + len(clue):]
    txn_id_end_del = txn_id_start.index("\n")
    txn_id = txn_id_start[:txn_id_end_del]
    return txn_id


def print_test_msg(command):
    HEADER_COLOR = '\033[95m'
    END_COLOR = '\033[0m'
    print(HEADER_COLOR)
    print("-----------------------")
    print('Testing {}.'.format(command))
    print("-----------------------")
    print(END_COLOR)


def print_success():
    PASSED_COLOR = '\033[92m'

    END_COLOR = '\033[0m'
    print(PASSED_COLOR)
    print("-----------------------")
    print('PASSED')
    print("-----------------------")
    print(END_COLOR)


def print_test_info(payout_address, txn_id):
    mining_detail = 'https://www.blocktrail.com/BTC/address/{}/transactions'.format(
        payout_address)
    buy_txn_id = 'https://www.blocktrail.com/BTC/tx/{}'.format(txn_id)
    link_color = '\033[94m'
    END_COLOR = '\033[0m'
    print(link_color)
    print("-----------------------")
    print("Details:")
    print("21 mine info: " + mining_detail)
    print("21 buy info: " + buy_txn_id)
    print("-----------------------")
    print(END_COLOR)


if __name__ == "__main__":
    test_end_to_end()
