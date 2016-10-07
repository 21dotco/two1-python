"""Manages configuration variables for the two1 CLI."""
# standard python imports
import os
import json
import time
import logging
import sys

import click

# two1 imports
from two1.commands.util import zerotier
import two1
import two1.commands.util.exceptions as exceptions
import two1.commands.util.uxstring as uxstring
import two1.commands.util.version as version
import two1.wallet as wallet


# Creates a ClickLogger
logger = logging.getLogger(__name__)


class Config:
    """Store information required to run two1 commands."""

    DEFAULTS = dict(username=None,
                    sellprice=10000,
                    contact='two1@21.co',
                    stdout='.two1/two1.stdout',
                    stderr='.two1/two1.stderr',
                    sortby='price',
                    maxspend=20000,
                    verbose=False,
                    mining_auth_pubkey=None,
                    auto_update=False,
                    wallet_path=wallet.Two1Wallet.DEFAULT_WALLET_PATH,
                    collect_analytics=True,
                    update_check_interval=3600)

    def __init__(
            self, config_file=two1.TWO1_CONFIG_FILE, config=None, check_update=False):
        """Return a new Config object with defaults plus custom properties.
           the `config_file` is used to load any config variables found on the
           system, and then the `config` input dictionary is used as the final
           override.
        """
        # Load configuration defaults
        self.state = {key: val for key, val in Config.DEFAULTS.items()}

        if not isinstance(config_file, str):
            raise TypeError('Parameter "config_file" must be a filename.')
        self.config_abs_path = os.path.expanduser(config_file)

        self.load_file_config(config_file)

        # Override defaults with any custom configuration
        if config:
            self.load_dict_config(config)

        if check_update:
            self.check_update()

        self.leave_zerotier()

    def check_update(self):
        """
        Check for any new updates to 21
        """
        do_update_check = False
        try:
            if 'last_update_check' not in self.state:
                do_update_check = True
            elif self.last_update_check < time.time() - self.update_check_interval:
                do_update_check = True
        except TypeError:
            do_update_check = True
        if do_update_check:
            actual_version = two1.TWO1_VERSION
            latest_version = version.get_latest_two1_version_pypi()
            self.set('last_update_check', time.time(), should_save=True)
            if not version.is_version_gte(actual_version, latest_version):
                click.echo(click.style(uxstring.UxString.update_required, fg='red'), file=sys.stderr)

    def leave_zerotier(self):
        """
        Leave ZeroTier networks to migrate users to new market.
        """
        if not self.state.get('zt_upgraded'):
            zerotier.leave_all()
        self.set('zt_upgraded', True, should_save=True)

    def load_file_config(self, config_file):
        """Set config properties based on a file."""
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

    def set(self, key, value, should_save=False):
        """Updates the config value and save updated config to disk.

        Args:
            key (str): key of the value you wish to update
            value (any): value being updated
        """
        self.state[key] = value
        if should_save:
            self.save()

    def save(self):
        """ Saves the config values to a file """
        with open(self.config_abs_path, mode='w') as f:
            f.write(json.dumps(self.state, indent=2, sort_keys=True))

    def __getattr__(self, key):
        """Look up a config property."""
        if key not in self.state:
            raise AttributeError()
        return self.state[key]

    def __repr__(self):
        """Return a printable version of the config state."""
        sorted_keys = sorted(self.state.keys())
        fmt_keys = ['{}: {}'.format(key, self.state[key]) for key in sorted_keys]
        return '<Config {}>'.format(', '.join(fmt_keys))
