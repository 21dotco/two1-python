"""Manages configuration variables for the two1 CLI."""
import os
import json

import two1
import two1.lib.wallet as wallet
import two1.lib.channels as channels
import two1.commands.util.exceptions as exceptions


class Config:

    """Stores information required to run two1 commands."""

    DEFAULTS = dict(username=None,
                    sellprice=10000,
                    contact='two1@21.co',
                    stdout='.two1/two1.stdout',
                    stderr='.two1/two1.stderr',
                    bitin='.bitcoin/wallet.dat',
                    bitout='.bitcoin/wallet.dat',
                    sortby='price',
                    maxspend=20000,
                    verbose=False,
                    mining_auth_pubkey=None,
                    auto_update=False,
                    wallet_path=wallet.Two1Wallet.DEFAULT_WALLET_PATH,
                    collect_analytics=False)

    def __init__(self, config_file=two1.TWO1_CONFIG_FILE, config=None):
        """Return a new Config object with defaults plus custom properties."""
        # Load configuration defaults
        self.state = {key: val for key, val in Config.DEFAULTS.items()}
        # Override defaults with any custom configuration
        self.load_dict_config(config) if config else self.load_file_config(config_file)

    def load_file_config(self, config_file):
        """Set config properties based on a file."""
        if not isinstance(config_file, str):
            raise TypeError('Parameter "config_file" must be a filename.')
        self.config_abs_path = os.path.expanduser(config_file)

        # Create the directory if it does not exist
        if not os.path.exists(os.path.dirname(self.config_abs_path)):
            os.makedirs(os.path.dirname(self.config_abs_path))

        try:
            # Load the configuration file contents into a dictionary
            with open(self.config_abs_path, mode='r') as f:
                self.load_dict_config(json.loads(f.read()))
        except FileNotFoundError:
            # Create a configuration file with default values
            with open(self.config_abs_path, mode='w') as f:
                f.write(json.dumps(self.state, indent=2, sort_keys=True))
        except ValueError:
            raise exceptions.FileDecodeError(self.config_abs_path)

    def load_dict_config(self, config):
        """Set config properties based on a dictionary."""
        if not isinstance(config, dict):
            raise TypeError('Parameter "config" must be a dictionary type.')
        for key, value in config.items():
            self.state[key] = value

    def set(self, key, value):
        """Updates the config value and save updated config to disk.

        Args:
            key (str): key of the value you wish to update
            value (any): value being updated
        """
        self.state[key] = value
        with open(self.config_abs_path, mode='w') as f:
            f.write(json.dumps(self.state, indent=2, sort_keys=True))

    def __getattr__(self, key):
        """Look up a config property."""
        if key not in self.state:
            raise AttributeError()
        return self.state[key]

    def __repr__(self):
        """Return a printable version of the config state."""
        return '<Config {}>'.format(', '.join('{}: {}'.format(key, self.state[key]) for key in sorted(self.state.keys())))

    def log(self, msg, *args, nl=True, **kwargs):
        """ Logs a message to stdout using the click styling and echo functions

            If json only is enabled this function will not print anything

        Args:
            msg (str): the message to print
            args (list, tuple): message arguments when using a string formatter
            nl (bool): if set to true a newline is printed after the msg
            kwargs (dict): extra keyword args is used as syling params
        """
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
        """ Logs a message to stdout if the verbose flag is set

            If json only is enabled this function will not print anything

        Args:
            msg (str): message to print verbosely
            args (list): message arguments when using a string formatter
        """
        if self.verbose:
            self.log(msg, *args)

    def echo_via_pager(self, msg, color=None):
        """ Takes a message and shows it via an environment specific pager

            If json only is enabled this function will not print anything

        Args:
            msg (str): message to be shown  on pager
            color (str): controls if the pager shows ANSI colors or not
        """
        if not self.json_output:
            click.echo_via_pager(msg, color)

    def log_purchase(self, **kwargs):
        """
        Todo:
            remove this function... it does nothing
        """
        # simple logging to file
        # this can be replaced with pickle/sqlite
        return

    def get_purchases(self):
        """
        Todo:
            remove this function, it does nothing
        """
        # read all right now. TODO: read the most recent ones only
        return []

    def set_json_output(self, value):
        """ Sets the json output which is printed after the command is finished

        Args:
            value (dict):
        """
        self.json_output = value
