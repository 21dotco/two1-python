"""
Static analysis of source code.
"""
from subprocess import call

IGNORE_LIST = '--ignore=E101,E113,E121,E122,E123,E125,E126,E127,E128,E129,E203,E226,E231,E241,E251,E265,E302,E402,E501,E502,E712,E713,E731,F403,F811,F812,F841,W191,W293'  # nopep8


def test_flake8():
    exit_status = call(['flake8', '.', IGNORE_LIST])
    assert exit_status == 0
