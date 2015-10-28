import pytest
from click.testing import CliRunner
from two1.cli import main
import pexpect

integration = pytest.mark.skipif(
    not pytest.config.getoption("--integration"),
    reason="need --integration option to run"
)

@integration
def test_21_mine(cli_runner):
    child = cli_runner.spawn('mine')
    child.expect(pexpect.EOF)
    child.close()
    assert child.exitstatus == 0

    child = cli_runner.spawn('status')
    child.expect(pexpect.EOF)
    child.close()
    assert child.exitstatus == 0
