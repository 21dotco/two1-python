import pytest
import subprocess
import sys
from unittest.mock import MagicMock

from two1.wallet.daemonizer import get_daemonizer
from two1.wallet.daemonizer import Launchd
from two1.wallet.daemonizer import Systemd


def test_get_daemonizer():
    sys.platform = 'darwin'
    d = get_daemonizer()

    assert d == Launchd

    sys.platform = 'linux'
    Systemd.check_systemd = MagicMock(return_value=True)
    d = get_daemonizer()

    assert d == Systemd

    Systemd.check_systemd = MagicMock(return_value=False)
    with pytest.raises(OSError):
        d = get_daemonizer()

    sys.platform = 'win'
    with pytest.raises(OSError):
        d = get_daemonizer()


def test_systemd():
    sys.platform = 'linux'
    Systemd.check_systemd = MagicMock(return_value=True)
    d = get_daemonizer()

    Systemd.SERVICE_FILE_PATH.exists = MagicMock(return_value=True)
    Systemd.ENV_FILE_PATH.exists = MagicMock(return_value=True)
    assert d.installed()

    Systemd.ENV_FILE_PATH.exists = MagicMock(return_value=False)
    assert not d.installed()

    Systemd.SERVICE_FILE_PATH.exists = MagicMock(return_value=False)
    assert not d.installed()

    Systemd.ENV_FILE_PATH.exists = MagicMock(return_value=True)
    assert not d.installed()

    Systemd.SERVICE_FILE_PATH.exists = MagicMock(return_value=True)
    dpo = dict(provider='chain',
               api_key_id="ID",
               api_key_secret="SECRET")
    assert d.install(dpo)

    Systemd.SERVICE_FILE_PATH.exists = MagicMock(side_effect=[False, True])
    Systemd.ENV_FILE_PATH.exists = MagicMock(side_effect=[True])
    Systemd.check_systemd = MagicMock(return_value=True)
    Systemd._write_env_file = MagicMock(return_value=True)
    Systemd._write_service_file = MagicMock(return_value=True)

    install_rv = d.install(dpo)
    assert Systemd.SERVICE_FILE_PATH.exists.call_count == 2
    assert install_rv

    Systemd.SERVICE_FILE_PATH.exists = MagicMock(side_effect=[False, True])
    Systemd.ENV_FILE_PATH.exists = MagicMock(side_effect=[False])
    Systemd.check_systemd = MagicMock(return_value=True)
    Systemd._write_env_file = MagicMock(return_value=True)
    Systemd._write_service_file = MagicMock(return_value=True)

    install_rv = d.install(dpo)
    assert Systemd.SERVICE_FILE_PATH.exists.call_count == 2
    assert not install_rv

    enabled_status = """● two1-wallet.service - two1 wallet daemon
   Loaded: loaded (/etc/systemd/user/two1-wallet.service; enabled)
   Active: failed (Result: exit-code) since Fri 2015-10-02 04:38:48 UTC; 2min 32s ago
  Process: 19151 ExecStart=/usr/local/bin/walletd (code=exited, status=203/EXEC)
 Main PID: 19151 (code=exited, status=203/EXEC)""".encode()

    disabled_status = """● two1-wallet.service - two1 wallet daemon
   Loaded: loaded (/etc/systemd/user/two1-wallet.service; disabled)
   Active: failed (Result: exit-code) since Fri 2015-10-02 04:38:48 UTC; 7min ago
 Main PID: 19151 (code=exited, status=203/EXEC)""".encode()

    active_status = """● two1-wallet.service - two1 wallet daemon
   Loaded: loaded (/etc/systemd/user/two1-wallet.service; enabled)
   Active: active (running) since Fri 2015-10-02 04:38:48 UTC; 2min 32s ago
 Main PID: 533 (walletd)
   CGroup: /usr/local/bin/walletd
           └─533 /usr/local/bin/walletd""".encode()

    subprocess.check_output = MagicMock(return_value=enabled_status)
    assert Systemd.enabled()

    subprocess.check_output = MagicMock(return_value=disabled_status)
    assert not Systemd.enabled()

    Systemd.SERVICE_FILE_PATH.exists = MagicMock(side_effect=[True, True])
    Systemd.ENV_FILE_PATH.exists = MagicMock(side_effect=[True, True])
    subprocess.check_output = MagicMock(side_effect=[b"", enabled_status])
    assert Systemd.enable()

    subprocess.check_output = MagicMock(side_effect=[b"", disabled_status])
    assert Systemd.disable()

    Systemd.SERVICE_FILE_PATH.exists = MagicMock(side_effect=[True, True])
    Systemd.ENV_FILE_PATH.exists = MagicMock(side_effect=[True, True])
    subprocess.check_output = MagicMock(side_effect=[enabled_status,
                                                     enabled_status,
                                                     b"",
                                                     active_status])
    assert Systemd.start()

    subprocess.check_output = MagicMock(side_effect=[active_status,
                                                     b"",
                                                     enabled_status])
    assert Systemd.stop()


def test_launchd():
    Launchd.PLIST_FILE_PATH.exists = MagicMock(side_effect=[True, False])
    assert Launchd.installed()
    assert not Launchd.installed()

    dpo = dict(provider='chain',
               api_key_id="ID",
               api_key_secret="SECRET")
    Launchd.PLIST_FILE_PATH.exists = MagicMock(side_effect=[True,
                                                            False, True,
                                                            False, False])
    Launchd._create_plist_file = MagicMock()
    assert Launchd.install(dpo)  # Already installed
    assert Launchd.install(dpo)  # Not installed, but gets installed
    assert not Launchd.install(dpo)  # Not installed, and problem installing

    # No point in testing Launchd.enabled/enable/disable as they all call into
    # the installed/uninstall functions anyway

    started_status = """{
	"LimitLoadToSessionType" = "Aqua";
	"Label" = "com.two1.walletd";
	"TimeOut" = 30;
	"OnDemand" = false;
	"LastExitStatus" = 0;
	"PID" = 46659;
	"Program" = "/usr/local/bin/walletd";
	"ProgramArguments" = (
		"/usr/local/bin/walletd";
	);
};""".encode()

    not_found_status = """Could not find service "com.two1.walletd" in domain for """.encode()

    subprocess.check_output = MagicMock(side_effect=[started_status,
                                                     not_found_status])
    assert Launchd.started()
    assert not Launchd.started()

    Launchd.PLIST_FILE_PATH.exists = MagicMock(side_effect=[True])
    subprocess.check_output = MagicMock(side_effect=[started_status])
    assert Launchd.start()

    Launchd.PLIST_FILE_PATH.exists = MagicMock(side_effect=[True, True])
    subprocess.check_output = MagicMock(side_effect=[not_found_status,
                                                     b"",
                                                     started_status])
    assert Launchd.start()

    Launchd.PLIST_FILE_PATH.exists = MagicMock(side_effect=[True, True])
    subprocess.check_output = MagicMock(side_effect=[not_found_status,
                                                     b"",
                                                     not_found_status])
    assert not Launchd.start()

    subprocess.check_output = MagicMock(side_effect=[started_status, b"",
                                                     not_found_status])
    assert Launchd.stop()
    assert Launchd.stop()
