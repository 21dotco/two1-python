import pytest
import pexpect
import random
import json
import os
from two1.tests import test_utils

import two1.tests.integration.test_basic_commands

test_map = {
    "21-mine": (two1.tests.integration.test_basic_commands.test_21_mine, 5),
    "21-status": (two1.tests.integration.test_basic_commands.test_21_status, 7),
    "21-log": (two1.tests.integration.test_basic_commands.test_21_log, 4),
    "21-log-raw": (two1.tests.integration.test_basic_commands.test_21_log_raw, 4),
    "21-status-raw": (two1.tests.integration.test_basic_commands.test_21_status_raw, 4),
    "21-buy-search": (two1.tests.integration.test_basic_commands.test_21_buy_search, 10),
    "21-buy-search-onchain": (two1.tests.integration.test_basic_commands.test_21_buy_search_onchain, 1),
    "21-buy-sms": (two1.tests.integration.test_basic_commands.test_21_buy_sms, 10),
    "21-buy-sms-onchain": (two1.tests.integration.test_basic_commands.test_21_buy_sms_onchain, 1),
    "User-sleep": (two1.tests.integration.test_basic_commands.random_sleep, 0),
    "21-flush": (two1.tests.integration.test_basic_commands.test_21_flush, 0),
}


def create_test_scenario(n):
    tests = []
    total = sum(w[1] for c, w in test_map.items())
    for i in range(n):
        if i == int(n/2) and pytest.config.getoption("--full-integration-inject-flush"):
            # We insert a flush in the middle if we need to flush.
            tests.append("21-flush")
            continue

        r = random.uniform(0, total)
        upto = 0
        for c, w in test_map.items():
            if upto + w[1] > r:
                tests.append(c)
                break
            upto += w[1]

    with open(os.path.join(os.path.dirname(__file__), "../../../integration_test_list.txt"), "w") as f:
        json.dump({"tests": tests}, f)

    return tests

def load_test_scenario(filename):
    with open(filename, "r") as f:
        test_json = json.load(f)
        return test_json['tests']

def get_test_scenario():
    v = None
    if pytest.config.getoption("--full-integration-file"):
        v = load_test_scenario(pytest.config.getoption("--full-integration-file"))
    else:
        v = create_test_scenario(pytest.config.getoption("--full-integration-number"))
    return v

@test_utils.full_integration
@pytest.mark.parametrize("name", get_test_scenario())
def test_integration(cli_runner, name):
    test_map[name][0](**locals())