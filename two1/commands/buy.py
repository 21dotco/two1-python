import json
import click
import datetime
import re

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


@click.group()
@click.option('-p', '--payment-method', default='bittransfer', type=click.Choice(['bittransfer', 'onchain', 'channel']))
@click.option('--max-price', default=10000, help="Maximum amount to pay")
@click.option('-i', '--info', 'info_only', default=False, is_flag=True, help="Retrieve initial 402 payment information.")
@click.pass_context
def buy(ctx, payment_method, max_price, info_only):
    """Buy API calls with mined bitcoin.

\b
Usage
-----
Execute a search query for bitcoin. See no ads.
$ 21 buy search "Satoshi Nakamoto"

\b
See the price in Satoshis of one bitcoin-payable search.
$ 21 buy --info search

\b
See the help for search.
$ 21 buy search -h

\b
See the price in Satoshis of one bitcoin-payable article.
$ 21 buy --info content http://on.wsj.com/1IV0HT5

\b
Buy an article with bitcoin.
$ 21 buy content http://on.wsj.com/1IV0HT5

\b
See the price of a bitcoin-payable priority message.
$ 21 buy --info social @balajis

\b
Direct message someone outside your social network for bitcoin.
$ 21 buy social @balajis "Hey nice to meet you, I'm @example. My startup is example.com"
"""
    ctx.obj["payment_method"] = payment_method
    ctx.obj["max_price"] = max_price
    ctx.obj["info_only"] = info_only


@click.argument('query', default="")
@buy.command()
@click.pass_context
def search(ctx, query=""):
    """Execute a search query for bitcoin. See no ads.

\b
Example
-------
$ 21 buy search "First Bitcoin Computer"
"""
    _buy(ctx.obj["config"],
         "search",
         dict(query=query),
         "GET",
         None,
         None,
         ctx.obj["payment_method"],
         ctx.obj["max_price"],
         ctx.obj["info_only"]
         )


@click.argument('message', default="")
@click.argument('twitter_user', default="@balajis")
@buy.command()
@click.pass_context
def social(ctx, message, twitter_user):
    """Send a paid message to someone outside your social network.

\b
Example
-------
$ 21 buy social @balajis "Hey nice to meet you, i'm @syassami"
"""
    _buy(ctx.obj["config"],
         "social",
         dict(message=message),
         "POST",
         None,
         None,
         ctx.obj["payment_method"],
         ctx.obj["max_price"],
         ctx.obj["info_only"]
         )


@click.argument('url', default="")
@buy.command()
@click.pass_context
def content(ctx, url):
    """Purchase online content without ads or login.

\b
Example
-------
$ 21 buy content http://on.wsj.com/1IV0HT5
"""
    _buy(ctx.obj["config"],
         "content",
         dict(url=url),
         "GET",
         None,
         None,
         ctx.obj["payment_method"],
         ctx.obj["max_price"],
         ctx.obj["info_only"]
         )



@capture_usage
def _buy(config, resource, data, method, data_file, output_file,
         payment_method, max_price, info_only):
    # If resource is a URL string, then bypass seller search
    if URL_REGEXP.match(resource):
        target_url = resource
        seller = target_url
    elif resource in DEMOS:
        target_url = TWO1_MERCHANT_HOST + DEMOS[resource]["path"]
        data = json.dumps(data)
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
            bit_req = BitTransferRequests(config.machine_auth, config.username)
        elif payment_method == 'onchain':
            bit_req = OnChainRequests(config.wallet)
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
