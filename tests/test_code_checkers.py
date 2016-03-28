"""
Static analysis of source code.
"""
from subprocess import call

IGNORE_LIST = '--ignore=E501,F401,E121,E265,E251,E127,W293,E302,F841,E203,E502,E221,E128,E122,W191,E303,W291,E712,W391,E231,E225,E261,F811,E111,E222,E202,E201,E126,E101,F812,F403,E713,E711,E272,E271,E262,E129,E125,E113,E241,E226,E123,E402,E731,E266,E116'  # nopep8


def test_flake8():
    exit_status = call(['flake8', '.', IGNORE_LIST])
    assert exit_status == 0
