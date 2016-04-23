"""Utility functions for user wallets."""
# standard python imports
import json
import os
import logging

# 3rd party imports
import click

# two1 imports
import two1
import two1.wallet as wallet
import two1.wallet.daemonizer as daemonizer
import two1.wallet.exceptions as exceptions
import two1.commands.util.uxstring as uxstring
import two1.blockchain.twentyone_provider as twentyone_provider


# Creates a ClickLogger
logger = logging.getLogger(__name__)


def get_or_create_wallet(wallet_path):
    """Create a new wallet or return the currently existing one."""
    data_provider = twentyone_provider.TwentyOneProvider(two1.TWO1_PROVIDER_HOST)

    if wallet.Two1Wallet.check_wallet_file(wallet_path):
        return wallet.Wallet(wallet_path=wallet_path, data_provider=data_provider)

    # configure wallet with default options
    click.pause(uxstring.UxString.create_wallet)

    wallet_options = dict(data_provider=data_provider, wallet_path=wallet_path)

    if not wallet.Two1Wallet.configure(wallet_options):
        raise click.ClickException(uxstring.UxString.Error.create_wallet_failed)

    # Display the wallet mnemonic and tell user to back it up.
    # Read the wallet JSON file and extract it.
    with open(wallet_path, 'r') as f:
        wallet_config = json.load(f)
        mnemonic = wallet_config['master_seed']

    click.pause(uxstring.UxString.create_wallet_done % click.style(mnemonic, fg='green'))

    # Start the daemon, if:
    # 1. It's not already started
    # 2. It's using the default wallet path
    # 3. We're not in a virtualenv
    try:
        d = daemonizer.get_daemonizer()

        if wallet.Two1Wallet.is_configured() and not os.environ.get("VIRTUAL_ENV") and not d.started():
            d.start()
            if d.started():
                logger.info(uxstring.UxString.wallet_daemon_started)
    except (OSError, exceptions.DaemonizerError):
        pass

    if wallet.Two1Wallet.check_wallet_file(wallet_path):
        return wallet.Wallet(wallet_path=wallet_path, data_provider=data_provider)
