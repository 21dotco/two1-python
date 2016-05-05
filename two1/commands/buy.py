"""Buy from a machine-payable endpoint."""
# standart python imports
import re
import sys
import json
import urllib.parse
import logging

# 3rd party imports
import click

# two1 imports
import two1.channels as channels
import two1.commands.util.uxstring as uxstring
import two1.bitrequests as bitrequests
import two1.commands.util.decorators as decorators
import two1.wallet.exceptions as wallet_exceptions
import two1.channels.statemachine as statemachine
import two1.commands.util.bitcoin_computer as bitcoin_computer


# Creates a ClickLogger
logger = logging.getLogger(__name__)


@click.command()
@click.argument('resource', nargs=2)
@click.option(
    '-i', '--info', 'info_only', default=False, is_flag=True, help="Retrieve initial 402 payment information."
)
@click.option('-p', '--payment-method', default='offchain', type=click.Choice(['offchain', 'onchain', 'channel']))
@click.option('-H', '--header', multiple=True, default=None, help="HTTP header to include with the request")
@click.option('-X', '--request', 'method', default='GET', help="HTTP request method")
@click.option('-o', '--output', 'output_file', default=None, help="Output file")
@click.option('-d', '--data', default=None, help="Data to send in HTTP body")
@click.option('--data-file', type=click.File('rb'), help="Data file to send in HTTP body")
@click.option('--maxprice', default=10000, help="Maximum amount to pay")
@click.pass_context
@decorators.catch_all
@decorators.capture_usage
def buy(ctx, resource, **options):
    """Buy API calls with bitcoin.

\b
Usage
-----
Buy a bitcoin-payable resource.
$ 21 buy <resource>

\b
Get state, city, latitude, longitude, and estimated population for a given zip code.
$ 21 buy "https://mkt.21.co/zipdata/collect?zip_code=94109" --maxprice 2750

"""
    # Get requested URL resource for `21 buy <URL>` syntax
    buy_url = resource[0]
    if buy_url is None or buy_url is "":
        logger.info(ctx.command.get_help(ctx))
        sys.exit()

    # Backwards compatibility for `21 buy url <URL>` syntax
    if resource[0] == 'url':
        buy_url = resource[1]

    _buy(ctx.obj['config'], ctx.obj['client'], ctx.obj['machine_auth'], buy_url, **options)


def _buy(config, client, machine_auth, resource, info_only=False, payment_method='offchain', header=(),
         method='GET', output_file=None, data=None, data_file=None, maxprice=10000):
    """Purchase a 402-enabled resource via CLI.

    This function attempts to purchase the requested resource using the
    `payment_method` and then write out its results to STDOUT. This allows a
    user to view results or pipe them into another command-line function.

    Args:
        config (two1.commands.config.Config): an object necessary for various
            user-specific actions, as well as for using the `capture_usage`
            function decorator.
        client (two1.server.rest_client.TwentyOneRestClient) an object for
            sending authenticated requests to the TwentyOne backend.
        machine_auth (two1.server.machine_auth.MachineAuthWallet): a wallet used
            for machine authentication.
        resource (str): a URI of the form scheme://host:port/path with `http`
            and `https` strictly enforced as required schemes.
        info_only (bool): if True, do not purchase the resource, and cause the
            function to write only the 402-related headers.
        payment_method (str): the payment method used for the purchase.
        header (tuple): list of HTTP headers to send with the request.
        method (str): the HTTP method/verb to make with the request.
        output_file (str): name of the file to redirect function output.
        data (str): serialized data to send with the request. The function will
            attempt to deserialize the data and determine its encoding type.
        data_file (str): name of the data file to send in HTTP body.
        maxprice (int): allowed maximum price (in satoshis) of the resource.

    Raises:
        click.ClickException: if some set of parameters or behavior cause the
            purchase to not complete successfully for any reason.
    """
    # Find the correct payment method
    if payment_method == 'offchain':
        requests = bitrequests.BitTransferRequests(machine_auth, config.username)
    elif payment_method == 'onchain':
        requests = bitrequests.OnChainRequests(machine_auth.wallet)
    elif payment_method == 'channel':
        requests = bitrequests.ChannelRequests(machine_auth.wallet)
    else:
        raise click.ClickException(uxstring.UxString.buy_bad_payment_method.format(payment_method))

    # Request user consent if they're creating a channel for the first time
    if payment_method == 'channel' and not requests._channelclient.list():
        confirmed = click.confirm(uxstring.UxString.buy_channel_warning.format(
            requests.DEFAULT_DEPOSIT_AMOUNT, statemachine.PaymentChannelStateMachine.PAYMENT_TX_MIN_OUTPUT_AMOUNT
        ), default=True)
        if not confirmed:
            raise click.ClickException(uxstring.UxString.buy_channel_aborted)

    # Parse the url and validate its format
    if re.match(r'^(((\w*)(\/){0,1})(\w*)){0,2}(\/){0,1}$', resource):
        resource = 'https://mkt.21.co/' + resource
    _resource = urllib.parse.urlparse(resource)

    # Assume `http` as default protocol
    if 'http' not in _resource.scheme:
        resource = 'http://' + resource

    # Retrieve 402-related header information, print it, then exit
    if info_only:
        response = requests.get_402_info(resource)
        return logger.info('\n'.join(['{}: {}'.format(key, val) for key, val in response.items()]))

    # Collect HTTP header parameters into a single dictionary
    headers = {key.strip(): value.strip() for key, value in (h.split(':') for h in header)}

    # Handle data if applicable
    if data or data_file:
        method = 'POST' if method == 'GET' else method
        data, headers['Content-Type'] = _parse_post_data(data)

    # Make the paid request for the resource
    try:
        response = requests.request(
            method.lower(), resource, max_price=maxprice, data=data or data_file, headers=headers
        )
    except bitrequests.ResourcePriceGreaterThanMaxPriceError as e:
        raise click.ClickException(uxstring.UxString.Error.resource_price_greater_than_max_price.format(e))
    except wallet_exceptions.DustLimitError as e:
        raise click.ClickException(e)
    except ValueError as e:
        if bitcoin_computer.has_mining_chip():
            raise click.ClickException(uxstring.UxString.Error.insufficient_funds_mine_more)
        else:
            raise click.ClickException(uxstring.UxString.Error.insufficient_funds_earn_more)
    except Exception as e:
        raise click.ClickException(e)

    # Write response text to stdout or a filename if provided
    if not output_file:
        logger.info(response.content, nl=False)
    else:
        with open(output_file, 'wb') as f:
            logger.info(response.content, file=f, nl=False)

    logger.info('', err=True)  # newline for pretty-printing errors to stdout

    # Exit successfully if no amount was paid for the resource (standard HTTP request)
    if not hasattr(response, 'amount_paid'):
        return

    # Fetch and write out diagnostic payment information for balances
    if payment_method == 'offchain':
        twentyone_balance = client.get_earnings()["total_earnings"]
        logger.info(uxstring.UxString.buy_balances.format(response.amount_paid, '21.co', twentyone_balance), err=True)
    elif payment_method == 'onchain':
        onchain_balance = min(requests.wallet.confirmed_balance(), requests.wallet.unconfirmed_balance())
        logger.info(uxstring.UxString.buy_balances.format(response.amount_paid, 'blockchain', onchain_balance),
                    err=True)
    elif payment_method == 'channel':
        channel_client = requests._channelclient
        channel_client.sync()
        channels_balance = sum(s.balance for s in (channel_client.status(url) for url in channel_client.list())
                               if s.state == channels.PaymentChannelState.READY)
        logger.info(uxstring.UxString.buy_balances.format(response.amount_paid, 'payment channels', channels_balance),
                    err=True)


def _parse_post_data(data):
    """Parse a string into a data object that `requests` can use.

    Args:
        data (str): a serialized string consisting of key-value pairs

    Returns:
        dict: parsed dictionary of key-value pairs
        header: the appropriate `Content-Type` header for the data
    """
    JSON_HEADER = 'application/json'
    FORM_URLENCODED_HEADER = 'application/x-www-form-urlencoded'

    # Attempt to decode data as json
    try:
        json.loads(data)
        return data, JSON_HEADER
    except ValueError:
        pass

    # Attempt to decode data as form url-encoded
    url_data = {key: vals[0] for key, vals in urllib.parse.parse_qs(data).items()}
    if len(url_data.keys()):
        return data, FORM_URLENCODED_HEADER

    raise click.ClickException(uxstring.UxString.buy_bad_data_format)
