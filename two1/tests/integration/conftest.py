import os
import sys
import tempfile
import shutil
from two1.tests.integration.util import random_str
import pytest
from click.testing import CliRunner
import pexpect
import json
import requests
import subprocess
from two1.commands.config import Config, get_device_uuid



SINK_PAYOUT_ADDRESS = "12bVw5YTYqBghFxxZDwNCcAA78FKUNbWCJ"
SINK_USER = "twochainz"
DEFAULT_EMAIL = "corentin+pytest@21.co"

FP = os.fdopen(sys.stdout.fileno(), 'wb')

@pytest.yield_fixture(scope="session")
def temp_folder():
    # I tried using isolated_filesystem but the contextmanager stuff got me really
    # confused so instead I just moved the code here. The stupid thing is that isolated_filesystem
    # is a subfunction of Runner when it actually doesn't use it AT ALL. It should be a util.
    cwd = os.getcwd()
    t = tempfile.mkdtemp()
    os.chdir(t)
    print("TEST - Test working directory=" + t)

    try:
        yield t
    finally:
        os.chdir(cwd)
        try:
            shutil.rmtree(t)
        except (OSError, IOError):
            pass

@pytest.fixture(scope="session")
def config(request, temp_folder):
    def fin():
        # TODO delete the config
        pass
    request.addfinalizer(fin)
    return full_config

class CLI21():
    '''
    Helpers to manipulate the CLI21 as an object for testing.
    Is provided by fixtures cli_runner and cli_runner_uninit
    '''

    def __init__(self, temp_folder=None, wallet_path=None, config_path=None):

        self.existing_wallet = False
        self.config = None
        self.temp_folder = temp_folder
        self.wallet_path = wallet_path
        self.config_str_path = config_path
        if self.wallet_path or self.config_str_path:
            if not(self.wallet_path and self.config_str_path):
                raise EnvironmentError("wallet_path and config_path must be set together")
            self.existing_wallet = True
        elif self.temp_folder:
            self.existing_wallet = False
        else:
            raise EnvironmentError("temp_folder or wallet_path or config_path must be provided")

        self.config_str = ""
        self.walletCreated = False
        self.minerdRunning = False
        self.username = None

        self.env = {}
        for v in os.environ:
            if v.startswith("TWO1"):
                self.env[v] = os.environ[v]
        self.env["LC_ALL"] = "en_US.UTF-8"
        self.env["LANG"] = "en_US.UTF-8"

        self._init_config()

    def _init_config(self):
        print("CLI21 - Creating the config that is going to be used -------")
        config = []

        if not self.existing_wallet:
            filename = random_str(8) + ".json"
            self.config_str_path = os.path.join(self.temp_folder, filename)
            self.wallet_path = os.path.join(self.temp_folder, "wallet", "wallet_" + filename)

        config.append("--config-file={} ".format(self.config_str_path))
        config.append("--config wallet_path " + self.wallet_path)

        config_str = " ".join(config)
        print("CLI21 - Config = " + config_str)
        print("CLI21 - DONE - Creating the config that is going to be used -------")
        self.config_str = config_str

    def _set_config(self):
        # FIXME Find a user-visible to perform that type of operation. For now, using the code.
        # Keeping the hack contained here as much as possible.
        self.config = Config(self.config_str_path, (("wallet_path", self.wallet_path),))

    def init_wallet(self):
        '''
        Initializes the wallet with a random user by calling two1 status.
        '''
        if self.existing_wallet:
            print("Using existing Wallet. Not initializing.")
            self._set_config()
            return

        print("CLI21 - Creating the user & wallet -----------")
        child = self.spawn("status")
        child.expect("Press any key ...", timeout=30)
        child.send('\n')
        child.expect("Press any key ...")
        child.send('\n')

        self.username = "pytest_" + random_str(12)
        child.expect("Enter your email address:", timeout=30)
        child.sendline(DEFAULT_EMAIL)
        child.expect("Enter a username for your 21.co account:", timeout=30)
        child.sendline(self.username)
        child.expect("\[y\/N\]:") # "This may help us debug any issues and improve software quality. [y/N]:" also, backslashed because it is not a regexp
        child.sendline("y")
        child.expect(pexpect.EOF)
        child.close()
        print("CLI21 - Starting wallet daemon... -------------------")
        try:
            self.wallet_daemon_process = subprocess.Popen(
                ["walletd", "-wp", self.wallet_path])
        except Exception as e:
            raise(e)
        self.walletCreated = True
        self._set_config()
        print("CLI21 - DONE - Creating the user & wallet -----------")

    def _cli_cmd(self, cmd):
        return "two1" + " " + self.config_str + " "+ cmd

    def stop_minerd(self):
        if self.minerdRunning:
            print("Shutting down minerd..")
            try:
                subprocess.check_call(["sudo", "minerd", "--stop"])
            except subprocess.CalledProcessError:
                print("Minerd failed stopping. Please go terminate it manually.")

    def stop_walletd(self):
        print("Shutting down walletd..")
        try:
            self.wallet_daemon_process.kill()
        except Exception as e:
            print(e)

    def is_running_on_bc(self):
        return get_device_uuid() != None

    def sweep_wallet(self):
        if self.walletCreated:
            print("CLI21 - Sweeping the wallet -------")
            # Step 1 is sweep
            wallet_error = None
            try:
                print("sweep command: " + "wallet -wp " + self.wallet_path + " sweep " + SINK_PAYOUT_ADDRESS)
                (command_output, exitstatus) = pexpect.run("wallet -wp " + self.wallet_path + " sweep " + SINK_PAYOUT_ADDRESS, logfile=FP, withexitstatus=True)
            except e:
                wallet_error = e

            # Step 2 is transfer all the earnings
            self._flush_21_satoshis()

            # Raise the wallet error after we've flushed.
            if wallet_error:
                raise e
            print("CLI21 - DONE - Sweeping the wallet -------")

    def cleanup(self):
        self.stop_minerd()
        self.sweep_wallet()
        self.stop_walletd()

    def _flush_21_satoshis(self):
        # FIXME Find a user-visible to perform that type of operation. For now, using the code.
        # Keeping the hack contained here as much as possible.
        from two1.lib.server import rest_client
        from two1.commands.config import TWO1_HOST

        config = self.config
        client = rest_client.TwentyOneRestClient(TWO1_HOST,
                                             config.machine_auth,
                                             config.username)
        data = client.get_earnings()
        total_earnings = data["total_earnings"]
        bittransfer = {
            "amount": total_earnings,
            "payee_username": SINK_USER,
            "payer": config.username,
            "payout_address": SINK_PAYOUT_ADDRESS,
            "description": "Pytest integration sweeping earnings"
        }
        bittransfers = json.dumps(bittransfer)
        signature = config.machine_auth.sign_message(bittransfers)
        json_body = {
            "bittransfer": bittransfers,
            "signature": signature
        }

        print("Bittransfering " + str(total_earnings) + " satoshis to " + SINK_USER)

        response = requests.post(
            TWO1_HOST + "/pool/account/"+SINK_USER+"/bittransfer/",
            data=json.dumps(json_body),
            headers={"content-type":"application/json"})
        assert response.status_code == 200

    def sync_onchain_balance(self):
        from two1.lib.wallet import Wallet
        # explicitly sync wallet cache (auto-synced w/ 25 sec period)
        wallet = Wallet(self.wallet_path)
        wallet.sync_wallet_file()

    def get_status(self):
        """Get current status using the '21 status' command.
        """
        child = self.spawn('status --json')
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
        status = json.loads(s)
        child.close()
        assert child.exitstatus == 0
        return status

    def spawn(self, cmd, **extra):
        '''
        Spawns a `two1` command with pexpect.spawn
        The two1 and config portions are automatically added. The child (return object)
        can be used to expect strings, insert inputs or query what was printed by the CLI.
        It is the responsibility of the caller to cleanup the child (by calling close()).

        Args:
            cmd: str with the actual cli command. example: "status"
            **extra: any pexpect's spawn argument, with the exception of env and logfile.
        Returns:
            a pexpect.spawn return object (usually called child)
        '''

        print ("Spawning: "+ self._cli_cmd(cmd))
        return pexpect.spawn(self._cli_cmd(cmd), env=self.env, logfile=FP, **extra)

    def run(self, cmd, **extra):
        '''
        Runs a `two1` command with pexpect.run
        The two1 and config portions are automatically added. The child (return object)
        can be used to query what was printed by the CLI or the return code.

        Args:
            cmd: str with the actual cli command. example: "status"
            **extra: any pexpect's spawn argument, with the exception of env and logfile.
        Returns:
            a pexpect.run return object (usually called child)
        '''
        print ("Running: "+ self._cli_cmd(cmd))
        return pexpect.run(self._cli_cmd(cmd), env=self.env, logfile=FP, **extra)

def cli_runner_create(request, temp_folder):
    config_path = pytest.config.getoption("--integration-cli-config-path")
    wallet_path = pytest.config.getoption("--integration-cli-wallet-path")

    runner = CLI21(
        temp_folder=temp_folder,
        config_path=config_path,
        wallet_path=wallet_path
        )
    def fin():
        runner.cleanup()
    request.addfinalizer(fin)
    return runner

@pytest.fixture(scope="session")
def cli_runner_uninit(request, temp_folder):
    '''
    This fixture provides a CLI21 that was not initialized with a user or wallet.
    The first command that is going to run with this CLI will prompt for a user and
    acceptance of the wallet creation.

    It can be used to test the wallet creation, the user creation etc...
    '''
    return cli_runner_create(request, temp_folder)

@pytest.fixture(scope="session")
def cli_runner(request, temp_folder):
    '''
    This fixture provides a CLI21 that is already initialized with a brand new user and wallet.
    it takes longer to create than the uninit one but is ready to use out of the box.
    '''
    runner = cli_runner_create(request, temp_folder)
    runner.init_wallet()
    return runner
