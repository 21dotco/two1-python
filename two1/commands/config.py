import sys
import json
from os.path import join, dirname
import os
import two1
import click
from codecs import open
from path import path
from pathlib import Path
from two1.lib.blockchain.twentyone_provider import TwentyOneProvider
from two1.lib.wallet import daemonizer
from two1.lib.wallet.exceptions import DaemonizerError
from two1.lib.wallet.two1_wallet import Two1Wallet
from two1.lib.wallet.two1_wallet import Wallet
from two1.lib.server.machine_auth_wallet import MachineAuthWallet
from two1.lib.wallet import test_wallet
from two1.lib.util.uxstring import UxString

# if there is a .env in the root directory, use the endpoints that are specified in there


def parse_dotenv(dotenv_path):
    with open(dotenv_path, "rt") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            v = v.strip("'").strip('"')
            yield k, v


def load_dotenv(dotenv_path):
    """
    Read a .env file and load into os.environ.
    """
    for k, v in parse_dotenv(dotenv_path):
        os.environ.setdefault(k, v)
    return True

base_dir = str(Path(__file__).parents[2])
dotenv_path = join(base_dir, '.env')

if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
    click.secho("Reading endpoints from file: {}".format(dotenv_path),
                fg="yellow")

TWO1_USER_FOLDER = os.path.expanduser('~/.two1/')
TWO1_CONFIG_FILE = path(TWO1_USER_FOLDER + 'two1.json')
TWO1_HOST = os.environ.get("TWO1_HOST", "https://api.21.co")
TWO1_PROVIDER_HOST = os.environ.get("TWO1_PROVIDER_HOST", "https://blockchain.21.co")
TWO1_PYPI_HOST = os.environ.get("TWO1_PYPI_HOST", "https://pypi-3844.21.co")
TWO1_PACKAGE_NAME = "two1"
TWO1_LOGGER_SERVER = os.environ.get("TWO1_LOGGER_SERVER", "http://logger.21.co")
TWO1_POOL_URL = os.environ.get("TWO1_POOL_URL", "swirl+tcp://grid.21.co:21006")
TWO1_MERCHANT_HOST = os.environ.get("TWO1_MERCHANT_HOST", "http://market.21.co")
TWO1_VERSION = two1.__version__

try:
    TWO1_PATH = os.path.dirname(sys.argv[0])
except:
    TWO1_PATH = None

'''Primary use case for the following class is the singleton that holds
   all the state & config data required to run commands and subcommands
   for two1 app
'''


class Config(object):
    def __init__(self, config_file=TWO1_CONFIG_FILE, config=None, create_wallet=True):
        if not os.path.exists(TWO1_USER_FOLDER):
            os.makedirs(TWO1_USER_FOLDER)
        self.file = path(config_file).expand().abspath()
        self.dir = self.file.parent
        self.defaults = {}  # TODO: Rename this var. Those are not the defaults but the
        self.json_output = False # output in json
        #  actual config.
        self.load()
        # override config variables
        if config:
            if self.verbose:
                self.vlog("Applied manual config.")

            for k, v in config:
                self.defaults[k] = v
                if self.verbose:
                    self.vlog("\t{}={}".format(k, v))

        # add wallet object
        if self.defaults.get('testwallet', None) == 'y':
            self.wallet = test_wallet.TestWallet()
        elif create_wallet:
            dp = TwentyOneProvider(TWO1_PROVIDER_HOST)

            wallet_path = self.defaults.get('wallet_path')

            if not Two1Wallet.check_wallet_file(wallet_path):
                # configure wallet with default options
                click.pause(UxString.create_wallet)

                wallet_options = {
                    'data_provider': dp,
                    'wallet_path': wallet_path
                }

                if not Two1Wallet.configure(wallet_options):
                    raise click.ClickException(UxString.Error.create_wallet_failed)

                # Display the wallet mnemonic and tell user to back it up.
                # Read the wallet JSON file and extract it.
                with open(wallet_path, 'r') as f:
                    wallet_config = json.load(f)
                    mnemonic = wallet_config['master_seed']

                click.pause(UxString.create_wallet_done % (mnemonic))

            # Start the daemon, if:
            # 1. It's not already started
            # 2. It's using the default wallet path
            # 3. We're not in a virtualenv
            try:
                d = daemonizer.get_daemonizer()

                if Two1Wallet.is_configured() and \
                   wallet_path == Two1Wallet.DEFAULT_WALLET_PATH and \
                   not os.environ.get("VIRTUAL_ENV") and \
                   not d.started():
                    d.start()
                    if d.started():
                        click.echo(UxString.wallet_daemon_started)
            except (OSError, DaemonizerError):
                pass

            self.wallet = Wallet(wallet_path=wallet_path,
                                 data_provider=dp)
            self.machine_auth = MachineAuthWallet(self.wallet)
        else:
            # This branch is hit when '21 help' or '21 update' is invoked
            pass

    # pulls attributes from the self.defaults dict
    def __getattr__(self, name):
        if name in self.defaults:
            return self.defaults[name]
        else:
            # Default behaviour
            raise AttributeError

    def save(self):
        """Save config file, handling various edge cases."""
        if not self.dir.exists():
            self.dir.mkdir()
        if self.file.isdir():
            print("self.file=" + self.file)
            self.file.rmdir()
        with open(self.file + ".tmp", mode="w", encoding='utf-8') as fh:
            json.dump(self.defaults, fh, indent=2, sort_keys=True)
        # move file if successfully written
        os.rename(self.file + ".tmp", self.file)
        return self

    def load(self):
        """Load config from (1) self.file if extant or (2) from defaults."""
        if self.file.exists() and self.file.isfile():
            try:
                with open(self.file, mode="r", encoding='utf-8') as fh:
                    self.defaults = json.load(fh)
            except:
                print(UxString.Error.file_load % self.file)
                self.defaults = {}

        defaults = dict(username=None,
                        sellprice=10000,
                        contact="two1@21.co",
                        stdout=".two1/two1.stdout",
                        stderr=".two1/two1.stderr",
                        bitin=".bitcoin/wallet.dat",
                        bitout=".bitcoin/wallet.dat",
                        sortby="price",
                        maxspend=20000,
                        verbose=False,
                        mining_auth_pubkey=None,
                        auto_update=False,
                        wallet_path=Two1Wallet.DEFAULT_WALLET_PATH,
                        collect_analytics=False,
                        )

        save_config = False
        for key, default_value in defaults.items():
            if key not in self.defaults:
                self.defaults[key] = default_value
                save_config = True

        if save_config:
            self.save()

        return self

    def update_key(self, key, value):
        self.defaults[key] = value
        # might be better to switch to local sqlite for persisting
        # the config
        # self.save()

    # kwargs is styling parameters
    def log(self, msg, *args, nl=True, **kwargs):
        """Logs a message to stdout only if json is disabled."""
        if self.json_output:
            return
        if args:
            msg %= args
        if len(kwargs) > 0:
            out = click.style(msg, **kwargs)
        else:
            out = msg
        click.echo(out, nl=nl)

    def vlog(self, msg, *args):
        """Logs a message to stdout only if verbose is enabled and json is disabled."""
        if self.verbose:
            self.log(msg, *args)

    def echo_via_pager(self, msg, color=None):
        """Takes a text and shows it via an environment specific pager
           on stdout only if json is disabled."""
        if not self.json_output:
            click.echo_via_pager(msg, color)

    @property
    def device_uuid(self):
        uuid = None
        try:
            with open("/proc/device-tree/hat/uuid", "r") as f:
                uuid = f.readline().strip("\n")

        except FileNotFoundError:
            pass
        return uuid

    def log_purchase(self, **kwargs):
        # simple logging to file
        # this can be replaced with pickle/sqlite
        return

    def get_purchases(self):
        # read all right now. TODO: read the most recent ones only
        return []

    def set_json_output(self, value):
        self.json_output = value

    def fmt(self):
        pairs = []
        for key in sorted(self.defaults.keys()):
            pairs.append("%s: %s" % (key, self.defaults[key]))
        out = "file: %s\n%s\n""" % (self.file, "\n".join(sorted(pairs)))
        return out

    def __repr__(self):
        return "<Config\n%s>" % self.fmt()


# IMPORTANT: Suppose you want to invoke a command as a function
# for the purpose of testing, eg:
#
# >>> from two1.commands.search import search
# >>> search(silent=True)
#
# Then you *may* need to pass ensure=True and make sure that Config can
# self-initialize to a reasonable state purely with default arguments.
#
# The alternative is to make each command itself a thin wrapper around
# a library call with proper defaults (eg search calling search_lib).
# This will work only so long as we don't really need the config
# object within search_lib.
#
# For further details:
# http://click.pocoo.org/5/complex/#ensuring-object-creation
pass_config = click.make_pass_decorator(Config, ensure=False)
