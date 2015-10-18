import click
import datetime
import re

from two1.commands.config import pass_config
from two1.lib.bitcurl.bitrequests import BitRequests


URL_REGEXP = re.compile(
    r'^(?:http)s?://'  # http:// or https://
    # domain...
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'
    r'localhost|'  # localhost...
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
    r'(?::\d+)?'  # optional port
    r'(?:/?|[/?]\S+)$', re.IGNORECASE)


@click.command()
@click.argument('resource', nargs=1)
@click.option('-X', '--request', 'method', default='GET', help="HTTP request method")
@click.option('-d', '--data', default=None, help="Data to send in HTTP body")
@click.option('--data-file', type=click.File('rb'), help="Data file to send in HTTP body")
@click.option('-o', '--output', 'output_file', type=click.File('wb'), help="Output file")
@click.option('-p', '--payment-method', default='bitcheque', type=click.Choice(['bitcheque', 'onchain', 'channel']))
@click.option('--max-price', default=5000, help="Maximum amount to pay")
@pass_config
def buy(config, resource, data, method, data_file, output_file, payment_method, max_price):
    """Buy an API call with Bitcoin.

    \b
    Example:
    $ two1 buy en2cn --data '{"text": "This is SPARTA"}'
    Esto es SPARTA.
    $
    """

    # If resource is a URL string, then bypass seller search
    if URL_REGEXP.match(resource):
        target_url = resource
        seller = target_url
    else:
        raise NotImplementedError('Endpoint search is not implemented!')

    # Change default HTTP method from "GET" to "POST", if we have data
    if method == "GET" and (data or data_file):
        method = "POST"

    # Make the request
    try:
        br = BitRequests(config, payment_method)
        res = getattr(br, method.lower())(
            target_url,
            data=data or data_file
        )
    except Exception as e:
        config.log( str(e), fg="red")
        return

    # Write response text to output file or the console
    if output_file:
        output_file.write(res.content)
    else:
        config.log(res.text)

    # Record the transaction if it was a payable request
    if hasattr(res, 'paid_amount'):
        config.log_purchase(s=seller,
                            r=resource,
                            p=res.paid_amount,
                            d=str(datetime.datetime.today()))
