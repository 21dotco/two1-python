""" Two1 command help """
# standard python imports
import re
import logging

# 3rd party imports
import click

# two1 imports
from two1.commands.util import decorators


# Creates a ClickLogger
logger = logging.getLogger(__name__)


@click.command()
@click.option('--detail', is_flag=True, help="Show detailed help for 21.")
@click.pass_context
@decorators.catch_all
def help(ctx, detail):
    """Show help and exit."""
    # pylint: disable=redefined-builtin
    logger.info('', err=True)
    if not detail:
        logger.info(ctx.parent.get_help())
    else:
        out = """\
Summary
  =======
  21 allows developers to earn bitcoin on every HTTP request. Your
  installation includes this command line interface and a Python library
  called two1. Here is what you can do with 21:

   - Run 21 earn to get bitcoin on any device
   - Try 21 sell to rent out your machine for bitcoin
   - Import the two1 library to add micropayments to old or new apps
   - Use 21 publish to put your APIs on the 21 Marketplace
   - View your balance with 21 status, and receipts with 21 log
   - Check your 21 account with 21 profile

  Try the following examples at the command line, and then go to
  21.co/learn/intro-to-21 for an interactive tutorial.
  \b
  Install
  -------
  curl https://21.co | sh   # Install or update 21
  21 doctor                 # Confirm installation works
  21 uninstall              # Uninstall 21 and its dependencies
  \b
  Get bitcoin
  -----------
  21 faucet                 # Request bitcoin from 21 faucet
  21 buybitcoin             # Buy bitcoin via Coinbase
  21 status                 # View your current bitcoin balance
  21 log                    # See all past purchases and earnings
  \b
  Buy APIs
  --------
  21 search                 # Find an API to purchase in the 21 Marketplace
  21 buy $URL               # Buy it for bitcoin over HTTP
  21 rate $ID $RATING       # Rate the API you just purchased
  \b
  Sell/Publish APIs
  -----------------
  21 sell start --all       # Start selling the default bitcoin-payable APIs
  21 sell status            # See status of your servers and earnings
  21 publish submit a.yaml  # Publish custom API to 21 Marketplace
  \b
  Finish up
  ---------
  21 profile                # View your profile in the browser
  21 flush                  # Flush your bitcoin to the blockchain
"""
        oldhelp = ctx.parent.get_help()
        match = "For detailed help, run 21 help --detail"
        newhelp = re.sub(match,
                         out + "\n  " + match,
                         oldhelp)
        logger.info(newhelp)
