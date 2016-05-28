"""
Static analysis of source code.
"""
from subprocess import call


def test_flake8():
    exit_status = call(['flake8', '.'])
    assert exit_status == 0
