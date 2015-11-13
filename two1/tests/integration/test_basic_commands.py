import pytest
import pexpect
import random
import json
import os
import math
import time
from two1.tests import test_utils
from two1.tests.integration.decorators import verify_balances

# test constants (in satoshi)
PREVIOUS_MINE_TIMEDOUT = False
MAX_FEE = 10000
COST_PER_SMS = 1000
COST_PER_SEARCH = 800
REWARD_PER_MINE = 20000

@verify_balances()
@test_utils.integration
def test_21_status_raw(cli_runner, **kwargs):
    # status assert balances > 0, username != null, payout addr !=null
    child = cli_runner.spawn('status')
    child.expect(pexpect.EOF)
    child.close()
    assert child.exitstatus == 0

@verify_balances()
@test_utils.integration
def test_21_status(cli_runner, **kwargs):
    # status assert balances > 0, username != null, payout addr !=null
    status = cli_runner.get_status()

    assert status['wallet']['wallet']['twentyone_balance'] >= 0
    assert status['wallet']['wallet']['flushing'] >= 0
    assert status['wallet']['wallet']['onchain'] >= 0
    assert status['wallet']['buyable']['buyable_sms'] >= 0
    assert status['wallet']['buyable']['sms_unit_price'] >= 500
    assert status['wallet']['buyable']['buyable_searches'] >= 0
    assert status['wallet']['buyable']['search_unit_price'] >= 500

    assert status['mining'] # I can't know more for sure.
    assert len(status['account']['address']) <= 35 and \
        len(status['account']['address']) >= 26
    assert status['account']['address'].startswith("1")
    if not cli_runner.existing_wallet:
        assert status['account']['username'].startswith("pytest_")

    return status

@verify_balances(balance_delta=+REWARD_PER_MINE)
@test_utils.integration
def test_21_mine(cli_runner, **kwargs):

    # Mining is only available on PI.
    if not cli_runner.config.device_uuid:
        # TODO: verify that the mining fails as expected on ubuntu/osx
        # FIXME: I am not sure there is a better way to check that we are on a BC
        # FIXME (cont.) see conftest.py
        pytest.skip("21 mine must run on a PI")
        return

    global PREVIOUS_MINE_TIMEDOUT
    if PREVIOUS_MINE_TIMEDOUT:
        # If a previous mine timedout... there is no need to run it
        # again because its going to timeout anyway (unless we get
        # super lucky.. but I wouldn't count on it.)
        return

    status = cli_runner.get_status()
    original_balance = status['wallet']['wallet']['twentyone_balance']

    # TODO We should branch depending if we are on the pi or on a mac
    child = cli_runner.spawn('mine')
    try:
        matched = child.expect([
                pexpect.EOF,
                "do 21 status to see your mining progress.\r\n"
            ],
            timeout=3600) #mining can take a whileeeee
    except pexpect.exceptions.TIMEOUT as e:
        PREVIOUS_MINE_TIMEDOUT = True
        raise e
    child.close()
    assert child.exitstatus == 0
    #TODO add more checks

    #Running log to catch some errors
    test_21_log_raw(cli_runner)

    if matched == 0:
        # Means we are running a CPU Mining
        status = cli_runner.get_status()
        after_balance = status['wallet']['wallet']['twentyone_balance']
        assert original_balance < after_balance
    else:
        # Means we are running on a bitcoinkit and just started minerd
        cli_runner.minerdRunning = True
        status = cli_runner.get_status()
        assert status['mining']['hashrate'] != "[ Unavailable ]"


@verify_balances()
@test_utils.integration
def test_21_log(cli_runner, **kwargs):
    child = cli_runner.spawn('log --json')
    matched = child.expect(
        [
            ".*(Reading endpoints from file).*\n",
            pexpect.EOF
        ]
    )
    if matched == 0:
        #In the case we had to remove the damn extra .env line.
        child.expect(pexpect.EOF)
    child.close()

    s = child.before.decode('utf-8')
    s = s.strip("\r\n")
    s = s.lstrip()
    s = s.rstrip()
    log = json.loads(s)
    child.close()
    assert child.exitstatus == 0
    return log

@verify_balances()
@test_utils.integration
def test_21_log_raw(cli_runner, **kwargs):
    child = cli_runner.spawn('log')
    child.expect("(press RETURN)")
    child.send("\n")
    child.read(1)
    child.send('q')
    child.expect(pexpect.EOF)
    child.close()
    assert child.exitstatus == 0

@pytest.mark.skipif(True, reason="Flush is too long to be standalone")
def test_21_flush(cli_runner, **kwargs):
    status = cli_runner.get_status()
    original_balance = status['wallet']['wallet']['twentyone_balance']
    if original_balance == 0:
        # In this case there is nothing to flush
        # TODO get the right flush behavior if the balance is empty.
        return
    assert status['wallet']['wallet']['flushing'] == 0

    log = test_21_log(cli_runner)
    original_log_len = len(log)

    child = cli_runner.spawn('flush')
    child.expect(pexpect.EOF)
    child.close()
    assert child.exitstatus == 0

    status = cli_runner.get_status()
    flushing_balance = status['wallet']['wallet']['flushing']
    assert flushing_balance == original_balance
    assert status['wallet']['wallet']['twentyone_balance'] == 0

    timeout = time.time() + 60*60*2   # 2 hours from now
    while True:
        log = test_21_log(cli_runner)
        if len(log) > original_log_len:
            print("Flush reached the log!")
            break
        else:
            assert time.time() < timeout
            print("Log still the same, sleeping for 90s..")
            time.sleep(90)

    log = test_21_log(cli_runner)
    last_log = log[0]
    assert last_log['reason'] == "flush_payout"
    assert last_log['amount'] == -1 * flushing_balance

    #Verify that status is unchanged.
    status = cli_runner.get_status()
    flushing_balance = status['wallet']['wallet']['flushing']
    assert flushing_balance == original_balance
    # twentyone_balance might not be zero if we mine shares with minerd
    assert status['wallet']['wallet']['twentyone_balance'] < original_balance

    timeout = time.time() + 60*60*5   # 5 hours from now
    while True:
        status = cli_runner.get_status()
        if status['wallet']['wallet']['flushing'] != flushing_balance:
            print("Our flushing balance has changed")
            break
        else:
            assert time.time() < timeout
            print("Flushing balance is still the same, waiting for the flush to be confirmed")
            time.sleep(180)

    status = cli_runner.get_status()
    assert status['wallet']['wallet']['onchain'] == original_balance
    assert status['wallet']['wallet']['flushing'] == 0
    assert status['wallet']['wallet']['twentyone_balance'] == 0

@verify_balances(balance_delta=-COST_PER_SEARCH)
@test_utils.integration
def test_21_buy_search(cli_runner, **kwargs):
    searches = [
        'London',
        'Paris',
        "Satoshi Nakamoto",
        "Bitcoin",
        "21 Inc",
        "What do we do tonight Cortex?",
        "Take over the world",
        "Jessica Alba",
        "Why am I searching this?"
    ]

    i = random.randint(0, len(searches) - 1 )
    original_status = cli_runner.get_status()

    child = cli_runner.spawn('buy search "'+ searches[i] +'"')
    child.expect(pexpect.EOF)
    child.close()

    #Running log to catch some errors
    test_21_log_raw(cli_runner)

    if original_status['wallet']['wallet']['twentyone_balance'] - original_status['wallet']['buyable']['search_unit_price'] >= 0:
        assert child.exitstatus == 0
        end_status = cli_runner.get_status()
        assert original_status['wallet']['buyable']['buyable_searches'] == end_status['wallet']['buyable']['buyable_searches'] + 1
        assert original_status['wallet']['wallet']['twentyone_balance'] == \
            end_status['wallet']['wallet']['twentyone_balance'] + original_status['wallet']['buyable']['search_unit_price']
    else:
        assert "Insufficient satoshis" in child.before.decode('utf-8')
        #assert child.exitstatus != 0 #FIXME!
        end_status = cli_runner.get_status()
        assert original_status['wallet']['buyable']['buyable_searches'] == end_status['wallet']['buyable']['buyable_searches']
        assert original_status['wallet']['wallet']['twentyone_balance'] == end_status['wallet']['wallet']['twentyone_balance']

@verify_balances(onchain_delta=-COST_PER_SEARCH, onchain_transactions=1)
@test_utils.integration
def test_21_buy_search_onchain(cli_runner, **kwargs):
    searches = [
        'London',
        'Paris',
        "Satoshi Nakamoto",
        "Bitcoin",
        "21 Inc",
        "What do we do tonight Cortex?",
        "Take over the world",
        "Jessica Alba",
        "Why am I searching this?"
    ]

    i = random.randint(0, len(searches) - 1 )
    original_status = cli_runner.get_status()

    child = cli_runner.spawn('buy -p onchain search "'+ searches[i] +'"')
    child.expect(pexpect.EOF)
    child.close()
    cli_runner.sync_onchain_balance()
    
    #Running log to catch some errors
    test_21_log_raw(cli_runner)

    if original_status['wallet']['wallet']['onchain'] - original_status['wallet']['buyable']['search_unit_price'] >= 1000:
        assert child.exitstatus == 0
        end_status = cli_runner.get_status()
        assert original_status['wallet']['buyable']['buyable_searches'] >= end_status['wallet']['buyable']['buyable_searches'] + 1
        assert original_status['wallet']['wallet']['onchain'] >= \
            end_status['wallet']['wallet']['onchain'] + original_status['wallet']['buyable']['search_unit_price']
        assert original_status['wallet']['wallet']['onchain'] - end_status['wallet']['wallet']['onchain'] - original_status['wallet']['buyable']['search_unit_price'] <= MAX_FEE
    else:
        assert "is not sufficient" in child.before.decode('utf-8')
        #assert child.exitstatus != 0 #FIXME!
        end_status = cli_runner.get_status()
        assert original_status['wallet']['buyable']['buyable_searches'] == end_status['wallet']['buyable']['buyable_searches']
        assert original_status['wallet']['wallet']['onchain'] == end_status['wallet']['wallet']['onchain']

@verify_balances(balance_delta=-COST_PER_SMS)
@test_utils.integration
def test_21_buy_sms(cli_runner, **kwargs):
    SUCCESS_TWILIO = "+15005550006"
    original_status = cli_runner.get_status()

    child = cli_runner.spawn('buy sms "'+ SUCCESS_TWILIO +'" "Hello World from Integration"')
    child.expect(pexpect.EOF)
    child.close()

    #Running log to catch some errors
    test_21_log_raw(cli_runner)

    if original_status['wallet']['wallet']['twentyone_balance'] - original_status['wallet']['buyable']['sms_unit_price'] >= 0:
        assert child.exitstatus == 0
        end_status = cli_runner.get_status()
        assert original_status['wallet']['buyable']['buyable_sms'] == end_status['wallet']['buyable']['buyable_sms'] + 1
        assert original_status['wallet']['wallet']['twentyone_balance'] == \
            end_status['wallet']['wallet']['twentyone_balance'] + original_status['wallet']['buyable']['sms_unit_price']
    else:
        assert "Insufficient satoshis" in child.before.decode('utf-8')
        #assert child.exitstatus != 0 #FIXME!
        end_status = cli_runner.get_status()
        assert original_status['wallet']['buyable']['buyable_sms'] == end_status['wallet']['buyable']['buyable_sms']
        assert original_status['wallet']['wallet']['twentyone_balance'] == end_status['wallet']['wallet']['twentyone_balance']

@verify_balances(onchain_delta=-COST_PER_SMS, onchain_transactions=1)
@test_utils.integration
def test_21_buy_sms_onchain(cli_runner, **kwargs):
    SUCCESS_TWILIO = "+15005550006"
    original_status = cli_runner.get_status()

    child = cli_runner.spawn('buy -p onchain sms "'+ SUCCESS_TWILIO +'" "Hello World from Integration"')
    child.expect(pexpect.EOF)
    child.close()

    cli_runner.sync_onchain_balance()

    #Running log to catch some errors
    test_21_log_raw(cli_runner)

    if original_status['wallet']['wallet']['onchain'] - original_status['wallet']['buyable']['sms_unit_price'] >= 1000:
        assert child.exitstatus == 0
        end_status = cli_runner.get_status()
        assert original_status['wallet']['buyable']['buyable_sms'] >= end_status['wallet']['buyable']['buyable_sms'] + 1
        assert original_status['wallet']['wallet']['onchain'] - original_status['wallet']['buyable']['sms_unit_price'] >= \
            end_status['wallet']['wallet']['onchain']
        assert original_status['wallet']['wallet']['onchain'] - end_status['wallet']['wallet']['onchain'] - original_status['wallet']['buyable']['sms_unit_price'] <= MAX_FEE
    else:
        assert "is not sufficient" in child.before.decode('utf-8')
        #assert child.exitstatus != 0 #FIXME!
        end_status = cli_runner.get_status()
        assert original_status['wallet']['buyable']['buyable_sms'] == end_status['wallet']['buyable']['buyable_sms']
        assert original_status['wallet']['wallet']['onchain'] == end_status['wallet']['wallet']['onchain']

@verify_balances()
def random_sleep(**kwargs):
    min_sleep = 1
    max_sleep = 600
    mu = 180
    sigma = 120
    duration = math.floor(min(max_sleep, max(min_sleep, random.gauss(mu, sigma))))
    print("Sleeping for " + str(duration) + " seconds...")
    time.sleep(duration)
