import json
import click
import datetime
import re

from two1.commands.config import pass_config
from two1.commands.config import TWO1_MERCHANT_HOST
from two1.commands.formatters import search_formatter
from two1.commands.formatters import social_formatter
from two1.commands.formatters import content_formatter
from two1.lib.server.analytics import capture_usage
from two1.lib.bitcurl.bitrequests import OnChainRequests
from two1.lib.bitcurl.bitrequests import BitTransferRequests


URL_REGEXP = re.compile(
    r'^(?:http)s?://'  # http:// or https://
    # domain...
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'
    r'localhost|'  # localhost...
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
    r'(?::\d+)?'  # optional port
    r'(?:/?|[/?]\S+)$', re.IGNORECASE)

DEMOS = {
    "search": {"path": "/search/bing", "formatter": search_formatter},
    "social": {"path": "/social/twitter", "formatter": social_formatter},
    "content": {"path": "/content/wsj", "formatter": content_formatter}
}


@click.command(context_settings=dict(ignore_unknown_options=True, allow_extra_args=True))
@click.argument('resource', nargs=1)
@click.option('-X', '--request', 'method', default='GET', help="HTTP request method")
@click.option('-d', '--data', default=None, help="Data to send in HTTP body")
@click.option('--data-file', type=click.File('rb'), help="Data file to send in HTTP body")
@click.option('-o', '--output', 'output_file', type=click.File('wb'), help="Output file")
@click.option('-p', '--payment-method', default='bittransfer', type=click.Choice(['bittransfer', 'onchain', 'channel']))
@click.option('--max-price', default=5000, help="Maximum amount to pay")
@click.option('-i', '--info', 'info_only', default=False, is_flag=True, help="Retrieve initial 402 payment information.")
@pass_config
@click.pass_context
def buy(ctx, config, resource, data, method, data_file, output_file, payment_method,
        max_price, info_only):
    """Buy API calls with mined bitcoin.

\b
Usage
-----
Search the internet, paying with bitcoin.
$ 21 buy search --query "Satoshi Nakamoto"

\b
See the price in Satoshis of one search, and the user hosting it.
$ 21 buy --info search

\b
See the price in Satoshis of one item of content.
$ 21 buy --info content

\b
See the price in Satoshis of a paid direct message via social network.
$ 21 buy --info social
"""
    _buy(config, ctx, resource, data, method, data_file, output_file,
         payment_method, max_price, info_only)


@capture_usage
def _buy(config, ctx, resource, data, method, data_file, output_file,
         payment_method, max_price, info_only):
    # If resource is a URL string, then bypass seller search
    if URL_REGEXP.match(resource):
        target_url = resource
        seller = target_url
    elif resource in DEMOS:
        target_url = TWO1_MERCHANT_HOST + DEMOS[resource]["path"]
        data = json.dumps(
            {ctx.args[i][2:]: ctx.args[i+1] for i in range(0, len(ctx.args), 2)}
        )
    else:
        raise NotImplementedError('Endpoint search is not implemented!')

    # Change default HTTP method from "GET" to "POST", if we have data
    if method == "GET" and (data or data_file):
        method = "POST"

    # Set default headers for making bitrequests with JSON-like data
    headers = {'Content-Type': 'application/json'}

    try:
        # Find the corrent payment method
        if payment_method == 'bittransfer':
            bit_req = BitTransferRequests(config)
        elif payment_method == 'onchain':
            bit_req = OnChainRequests(config)
        else:
            raise Exception('Payment method does not exist.')

        # Make the request
        if info_only:
            res = bit_req.get_402_info(target_url)
        else:
            res = bit_req.request(
                method.lower(), target_url, max_price=max_price,
                data=data or data_file, headers=headers)
    except Exception as e:
        config.log(str(e), fg="red")
        return

    # Output results to user
    if output_file:
        # Write response output file
        output_file.write(res.content)
    elif info_only:
        # Print headers that are related to 402 payment required
        for r in res:
            config.log('{}: {}'.format(r[0], r[1]))
    elif resource in DEMOS:
        config.log(DEMOS[resource]["formatter"](res))
    else:
        # Write response to console
        config.log(res.text)

    # Record the transaction if it was a payable request
    if hasattr(res, 'paid_amount'):
        config.log_purchase(s=seller,
                            r=resource,
                            p=res.paid_amount,
                            d=str(datetime.datetime.today()))
