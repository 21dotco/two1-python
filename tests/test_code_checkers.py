"""
Static analysis of source code.
"""
from subprocess import call

IGNORE_LIST = '--ignore=E123,E126,E226,E241,E501,E731,F403,F841'


def test_flake8():
    exit_status = call(['flake8', '.', IGNORE_LIST])
    assert exit_status == 0
