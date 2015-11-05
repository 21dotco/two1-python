import string
from click.testing import CliRunner
import random
from two1.cli import main
import pytest


def setup_wallet():
    runner = CliRunner()
    username = rand_str(5)
    wallet_creation_str = "\n\n" + username + "\n"
    runner.invoke(main, ['status'], input=wallet_creation_str)


def rand_str(length):
    return ''.join(
        random.choice(string.ascii_lowercase) for i in range(length))


integration = pytest.mark.skipif(
    not pytest.config.getoption("--integration"),
    reason="need --integration option to run"
)

full_integration = pytest.mark.skipif(
    not pytest.config.getoption("--full-integration-file") and \
    not pytest.config.getoption("--full-integration-number"),
    reason="need --full-integration option to run"
)