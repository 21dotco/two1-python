import string
from click.testing import CliRunner
import random
from two1.cli import main


def setup_wallet():
    runner = CliRunner()
    username = rand_str(5)
    wallet_creation_str = "\n\n" + username + "\n"
    runner.invoke(main, ['status'], input=wallet_creation_str)


def rand_str(length):
    return ''.join(
        random.choice(string.ascii_lowercase) for i in range(length))
