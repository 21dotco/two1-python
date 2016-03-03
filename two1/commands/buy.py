"""Buy from a machine-payable endpoint."""
import json
import datetime
import urllib.parse

import click

import two1
import two1.lib.server as server
import two1.lib.wallet.fees as fees
import two1.lib.channels as channels
import two1.commands.status as status
import two1.commands.util.uxstring as uxstring
import two1.lib.bitrequests as bitrequests
import two1.commands.util.decorators as decorators
import two1.lib.channels.statemachine as statemachine


@click.command()
@click.argument('resource', nargs=1)
@click.option('-i', '--info', 'info_only', default=False, is_flag=True, help="Retrieve initial 402 payment information.")
@click.option('-p', '--payment-method', default='offchain', type=click.Choice(['offchain', 'onchain', 'channel']))
@click.option('-H', '--header', multiple=True, default=None, help="HTTP header to include with the request")
@click.option('-X', '--request', 'method', default='GET', help="HTTP request method")
@click.option('-o', '--output', 'output_file', default=None, type=click.File('w'), help="Output file")
@click.option('-d', '--data', default=None, help="Data to send in HTTP body")
@click.option('--data-file', type=click.File('rb'), help="Data file to send in HTTP body")
@click.option('--maxprice', default=10000, help="Maximum amount to pay")
@click.pass_context
@decorators.capture_usage
def buy(ctx, resource, **options):
    """Buy API calls with mined bitcoin.

\b
Usage
-----
Send an SMS to a phone number.
$ 21 buy https://market.21.co/phone/send-sms --data 'phone=15005550002&text=hi'

"""
    _buy(ctx.obj['config'], ctx.obj['client'], ctx.obj['machine_auth'], resource, **options)


def _buy(config, client, machine_auth, resource, info_only=False, payment_method='offchain', header=(), method='GET', output_file=None, data=None, data_file=None, maxprice=10000):
    """Purchase a 402-enabled resource via CLI.

    This function attempts to purchase the requested resource using the
    `payment_method` and then write out its results to STDOUT. This allows a
    user to view results or pipe them into another command-line function.

    Args:
        config (two1.commands.config.Config): an object necessary for various
            user-specific actions, as well as for using the `capture_usage`
            function decorator.
        client (two1.lib.server.rest_client.TwentyOneRestClient) an object for
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
        confirmed = click.confirm(uxstring.UxString.buy_channel_warning.format(requests.DEFAULT_DEPOSIT_AMOUNT, statemachine.PaymentChannelStateMachine.PAYMENT_TX_MIN_OUTPUT_AMOUNT), default=True)
        if not confirmed:
            raise click.ClickException(uxstring.UxString.buy_channel_aborted)

    # Parse the url and validate its format
    _resource = urllib.parse.urlparse(resource)
    if 'http' not in _resource.scheme:
        raise click.ClickException(uxstring.UxString.buy_bad_uri_scheme)
    if len(_resource.netloc) == 0:
        raise click.ClickException(uxstring.UxString.buy_bad_uri_host)

    # Retrieve 402-related header information, print it, then exit
    if info_only:
        response = requests.get_402_info(resource)
        return click.echo('\n'.join(['{}: {}'.format(key, val) for key, val in response.items()]))

    # Collect HTTP header parameters into a single dictionary
    headers = {key.strip(): value.strip() for key, value in (h.split(':') for h in header)}

    # Handle data if applicable
    if data or data_file:
        method = 'POST' if method == 'GET' else method
        data, headers['Content-Type'] = _parse_post_data(data)

    # Make the paid request for the resource
    try:
        response = requests.request(method.lower(), resource, max_price=maxprice, data=data or data_file, headers=headers)
    except bitrequests.ResourcePriceGreaterThanMaxPriceError as e:
        raise click.ClickException(uxstring.UxString.Error.resource_price_greater_than_max_price.format(e))
    except Exception as e:
        raise click.ClickException(e)

    # Write response text to stdout or a filename if provided
    click.echo(response.text, file=output_file)

    # Exit successfully if no amount was paid for the resource (standard HTTP request)
    if not hasattr(response, 'amount_paid'):
        return

    # Fetch and write out diagnostic payment information for balances
    if payment_method == 'offchain':
        twentyone_balance = client.get_earnings()["total_earnings"]
        click.echo(uxstring.UxString.buy_balances.format(response.amount_paid, '21.co', twentyone_balance), err=True)
    elif payment_method == 'onchain':
        onchain_balance = min(requests.wallet.confirmed_balance(), requests.wallet.unconfirmed_balance())
        click.echo(uxstring.UxString.buy_balances.format(response.amount_paid, 'blockchain', onchain_balance), err=True)
    elif payment_method == 'channel':
        channel_client = requests._channelclient
        channel_client.sync()
        channels_balance = sum(s.balance for s in (channel_client.status(url) for url in channel_client.list())
                               if s.state == channels.PaymentChannelState.READY)
        click.echo(uxstring.UxString.buy_balances.format(response.amount_paid, 'payment channels', channels_balance), err=True)

    # Record the transaction if it was a payable request
    config.log_purchase(r=resource, p=response.amount_paid, d=str(datetime.datetime.today()))


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

    # Attempt to decode data as form url-encoded
    url_data = {key: vals[0] for key, vals in urllib.parse.parse_qs(data).items()}
    if len(url_data.keys()):
        return url_data, FORM_URLENCODED_HEADER

    # Attempt to decode data as json
    try:
        json_data = json.loads(data)
    except ValueError:
        raise click.ClickException(uxstring.UxString.buy_bad_data_format)

    return json_data, JSON_HEADER
